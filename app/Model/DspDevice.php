<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class DspDevice extends Model
{
    protected ?string $table = 'dsp_devices';

    protected array $fillable = [
        'license_key',
        'machine_code',
        'device_type',
        'bind_time',
        'last_active_time'
    ];
}
