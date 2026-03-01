<?php
declare(strict_types=1);

namespace App\Model;

use Hyperf\DbConnection\Model\Model;

/**
 * @property int $id
 * @property string $email
 * @property string $password_hash
 * @property string|null $password_plain
 * @property string|null $real_name
 * @property string|null $nickname
 * @property string|null $avatar
 * @property string $balance
 * @property int $points
 * @property int|null $parent_id
 * @property int|null $grandparent_id
 * @property string $invite_code
 * @property string $created_at
 * @property string|null $last_login_at
 * @property string $updated_at
 */
class User extends Model
{
    protected ?string $table = 'users';
    protected array $fillable = [
        'email','password_hash','password_plain','real_name','nickname','avatar',
        'balance','points','parent_id','grandparent_id','invite_code','last_login_at'
    ];
    protected array $casts = [
        'points' => 'integer',
        'parent_id' => 'integer',
        'grandparent_id' => 'integer',
    ];
}
