<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class LicenseLoginLog extends Model
{
    protected ?string $table = 'license_login_logs';

    protected array $fillable = [
        'license_key',
        'machine_code',
        'ip',
        'login_time',
        'result',
        'fail_reason'
    ];
}
