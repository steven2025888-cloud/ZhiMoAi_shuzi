<?php
declare(strict_types=1);

namespace App\Model;

use Hyperf\DbConnection\Model\Model;

class ChatEventsModel extends Model
{
    protected ?string $table = 'chat_events';

    // 不做任何字段保护，允许批量写入所有字段
    protected array $guarded = [];
}
