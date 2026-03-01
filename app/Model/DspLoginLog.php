<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class DspLoginLog extends Model
{
    protected ?string $table = 'dsp_login_logs';

    protected array $fillable = [
        'license_key',
        'machine_code',
        'ip',
        'login_time',
        'result',
        'fail_reason'
    ];
}
