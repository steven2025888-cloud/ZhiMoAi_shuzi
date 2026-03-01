<?php
declare(strict_types=1);

namespace App\Model;

use Hyperf\DbConnection\Model\Model;

class EmailCode extends Model
{
    protected ?string $table = 'email_codes';
    protected array $fillable = ['email','purpose','code','expires_at','used_at','ip'];
}
