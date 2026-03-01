<?php
namespace App\Model;

use Hyperf\Database\Model\Model;

class DspCard extends Model
{
    protected ?string $table = 'dsp_cards';

    protected array $fillable = [
        'license_key',
        'start_time',
        'end_time',
        'max_devices',
        'online_enabled',
        'status',
        'created_at',
        'updated_at'
    ];
    
    public function getEndTimeAttribute($value): ?string
    {
        if (!$value) return null;
        return substr((string)$value, 0, 10);
    }

    
}
