<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class TtsLog extends Model
{
    protected ?string $table = 'tts_logs';

    protected array $guarded = [];   // 内部系统，允许全字段写入
}
