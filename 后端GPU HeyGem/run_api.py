import argparse
import gc
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid

import queue
import cv2
from flask import Flask, request, jsonify, send_file

import service.trans_dh_service

from h_utils.custom import CustomError
from y_utils.config import GlobalConfig
from y_utils.logger import logger

app = Flask(__name__)


def write_video_api(
    output_imgs_queue,
    temp_dir,
    result_dir,
    work_id,
    audio_path,
    result_queue,
    width,
    height,
    fps,
    watermark_switch=0,
    digital_auth=0,
):
    output_mp4 = os.path.join(temp_dir, "{}-t.mp4".format(work_id))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    result_path = os.path.join(result_dir, "{}-r.mp4".format(work_id))
    video_write = cv2.VideoWriter(output_mp4, fourcc, fps, (width, height))
    logger.info("API VideoWriter init done")
    try:
        while True:
            state, reason, value_ = output_imgs_queue.get()
            if type(state) == bool and state == True:
                logger.info("API VideoWriter [{}]视频帧队列处理已结束".format(work_id))
                video_write.release()
                break
            else:
                if type(state) == bool and state == False:
                    logger.error(
                        "API VideoWriter [{}]任务视频帧队列 -> 异常原因:[{}]".format(work_id, reason)
                    )
                    raise CustomError(reason)
                for result_img in value_:
                    video_write.write(result_img)
        if video_write is not None:
            video_write.release()

        if watermark_switch == 1 and digital_auth == 1:
            logger.info("API VideoWriter [{}]任务需要水印和数字人标识".format(work_id))
            command = 'ffmpeg -y -i {} -i {} -i {} -i {} -filter_complex "overlay=(main_w-overlay_w)-10:(main_h-overlay_h)-10,overlay=(main_w-overlay_w)-10:10" -c:a aac -crf 15 -strict -2 {}'.format(
                audio_path, output_mp4,
                GlobalConfig.instance().watermark_path,
                GlobalConfig.instance().digital_auth_path,
                result_path,
            )
        elif watermark_switch == 1 and digital_auth == 0:
            logger.info("API VideoWriter [{}]任务需要水印".format(work_id))
            command = 'ffmpeg -y -i {} -i {} -i {} -filter_complex "overlay=(main_w-overlay_w)-10:(main_h-overlay_h)-10" -c:a aac -crf 15 -strict -2 {}'.format(
                audio_path, output_mp4,
                GlobalConfig.instance().watermark_path,
                result_path,
            )
        elif watermark_switch == 0 and digital_auth == 1:
            logger.info("API VideoWriter [{}]任务需要数字人标识".format(work_id))
            command = 'ffmpeg -loglevel warning -y -i {} -i {} -i {} -filter_complex "overlay=(main_w-overlay_w)-10:10" -c:a aac -crf 15 -strict -2 {}'.format(
                audio_path, output_mp4,
                GlobalConfig.instance().digital_auth_path,
                result_path,
            )
        else:
            command = "ffmpeg -loglevel warning -y -i {} -i {} -c:a aac -c:v libx264 -crf 15 -strict -2 {}".format(
                audio_path, output_mp4, result_path
            )
        logger.info("API command:{}".format(command))
        subprocess.call(command, shell=True)
        logger.info("API Video Writer write over, result: {}".format(os.path.realpath(result_path)))
        result_queue.put([True, result_path])
    except Exception as e:
        logger.error(
            "API VideoWriter [{}]视频帧队列处理异常结束，异常原因:[{}]".format(work_id, e.__str__())
        )
        result_queue.put(
            [False, "[{}]视频帧队列处理异常结束，异常原因:[{}]".format(work_id, e.__str__())]
        )
    logger.info("API VideoWriter 后处理进程结束")


service.trans_dh_service.write_video = write_video_api

# ---- 全局任务管理 ----
task_instance = None
task_results = {}  # code -> {"status": "processing"/"done"/"error", "result_path": ..., "error": ...}
task_lock = threading.Lock()


def init_task():
    """初始化数字人推理服务"""
    global task_instance
    sys.argv = [sys.argv[0]]
    task_instance = service.trans_dh_service.TransDhTask()
    time.sleep(10)
    logger.info("数字人推理服务初始化完成")


def run_task(audio_path, video_path, code, watermark_switch, digital_auth):
    """在后台线程中执行推理任务"""
    try:
        task_instance.task_dic[code] = ""
        task_instance.work(audio_path, video_path, code, 0, watermark_switch, digital_auth, 0)

        result_path = task_instance.task_dic.get(code, "")
        if isinstance(result_path, (list, tuple)) and len(result_path) > 2:
            result_path = result_path[2]

        # 将结果移到 result/<code> 目录
        final_result_dir = os.path.join("result", code)
        os.makedirs(final_result_dir, exist_ok=True)
        if result_path and os.path.exists(result_path):
            import shutil
            dest = os.path.join(final_result_dir, os.path.basename(result_path))
            shutil.move(result_path, dest)
            result_path = os.path.realpath(dest)

        with task_lock:
            task_results[code] = {"status": "done", "result_path": result_path}
        logger.info("[{}] 任务完成, 结果路径: {}".format(code, result_path))
    except Exception as e:
        logger.error("[{}] 任务异常: {}".format(code, traceback.format_exc()))
        with task_lock:
            task_results[code] = {"status": "error", "error": str(e)}


# ---- Flask API 路由 ----

@app.route("/easy/submit", methods=["POST"])
def submit_task():
    """
    提交数字人合成任务
    请求体 JSON:
    {
        "audio_url": "音频文件路径或URL",
        "video_url": "视频文件路径或URL",
        "code": "任务唯一标识（可选，不传则自动生成）",
        "watermark_switch": 0,
        "digital_auth": 0
    }
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"code": -1, "msg": "请求体必须是合法的JSON"}), 400

    audio_url = data.get("audio_url", "")
    video_url = data.get("video_url", "")
    code = data.get("code", str(uuid.uuid1()))
    watermark_switch = int(data.get("watermark_switch", 0))
    digital_auth = int(data.get("digital_auth", 0))

    if not audio_url or not video_url:
        return jsonify({"code": -1, "msg": "audio_url 和 video_url 不能为空"}), 400

    with task_lock:
        if code in task_results and task_results[code].get("status") == "processing":
            return jsonify({"code": -1, "msg": "任务 {} 正在处理中，请勿重复提交".format(code)}), 409
        task_results[code] = {"status": "processing"}

    t = threading.Thread(
        target=run_task,
        args=(audio_url, video_url, code, watermark_switch, digital_auth),
        daemon=True,
    )
    t.start()

    logger.info("任务已提交: code={}, audio={}, video={}".format(code, audio_url, video_url))
    return jsonify({"code": 0, "msg": "任务已提交", "data": {"code": code}})


@app.route("/easy/query", methods=["GET"])
def query_task():
    """
    查询任务状态
    参数: code=任务标识
    """
    code = request.args.get("code", "")
    if not code:
        return jsonify({"code": -1, "msg": "缺少参数 code"}), 400

    with task_lock:
        result = task_results.get(code)

    if result is None:
        return jsonify({"code": -1, "msg": "任务 {} 不存在".format(code)})

    if result["status"] == "processing":
        return jsonify({"code": 0, "msg": "任务处理中", "data": {"code": code, "status": "processing"}})
    elif result["status"] == "done":
        return jsonify({
            "code": 0,
            "msg": "任务完成",
            "data": {"code": code, "status": "done", "result_path": result.get("result_path", "")},
        })
    else:
        return jsonify({
            "code": -1,
            "msg": "任务失败: {}".format(result.get("error", "未知错误")),
            "data": {"code": code, "status": "error"},
        })


@app.route("/easy/download", methods=["GET"])
def download_result():
    """
    下载生成的视频结果
    参数: code=任务标识
    """
    code = request.args.get("code", "")
    if not code:
        return jsonify({"code": -1, "msg": "缺少参数 code"}), 400

    with task_lock:
        result = task_results.get(code)

    if result is None or result["status"] != "done":
        return jsonify({"code": -1, "msg": "任务未完成或不存在"}), 404

    result_path = result.get("result_path", "")
    if not result_path or not os.path.exists(result_path):
        return jsonify({"code": -1, "msg": "结果文件不存在"}), 404

    return send_file(result_path, mimetype="video/mp4", as_attachment=True,
                     download_name="{}.mp4".format(code))


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({"code": 0, "msg": "ok", "initialized": task_instance is not None})


def get_args():
    parser = argparse.ArgumentParser(
        description="数字人合成 API 服务",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API 监听地址")
    parser.add_argument("--port", type=int, default=8383, help="API 监听端口")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    logger.info("正在初始化数字人推理服务...")
    init_task()
    logger.info("启动 API 服务: {}:{}".format(args.host, args.port))
    app.run(host=args.host, port=args.port, threaded=True)

# 启动方式:
# python run_api.py
# python run_api.py --host 0.0.0.0 --port 8383
