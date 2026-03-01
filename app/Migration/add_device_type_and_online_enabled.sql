-- 1. dsp_cards 表增加 online_enabled 字段（默认0=仅本地版，1=支持在线版+本地版）
ALTER TABLE `dsp_cards` ADD COLUMN `online_enabled` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否支持在线版: 0=仅本地, 1=本地+在线' AFTER `max_devices`;

-- 2. dsp_devices 表增加 device_type 字段（pc / mobile）
ALTER TABLE `dsp_devices` ADD COLUMN `device_type` VARCHAR(10) NOT NULL DEFAULT 'pc' COMMENT '设备类型: pc, mobile' AFTER `machine_code`;

-- 3. dsp_cards 移除单一 machine_code 绑定，改用 dsp_devices 多设备管理
--    如果 dsp_cards 表有 machine_code 列，可以保留做兼容，也可以不管
--    新逻辑通过 dsp_devices 的 device_type 来区分 PC 和手机

-- 4. 给 dsp_devices 加唯一索引：同一个卡密 + 设备类型 只能绑定一台设备
ALTER TABLE `dsp_devices` ADD UNIQUE INDEX `uk_key_device_type` (`license_key`, `device_type`);
