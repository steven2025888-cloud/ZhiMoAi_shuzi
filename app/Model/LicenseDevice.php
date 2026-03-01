<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class LicenseDevice extends Model
{
    protected ?string $table = 'license_devices';

    protected array $fillable = [
        'license_key',
        'machine_code',
        'bind_time',
        'last_active_time'
    ];
}
