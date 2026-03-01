<?php
declare(strict_types=1);

namespace App\Model;

use Hyperf\DbConnection\Model\Model;

class UserToken extends Model
{
    protected ?string $table = 'user_tokens';
    protected array $fillable = ['user_id','token_hash','expires_at'];
}
