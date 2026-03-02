// uni_modules/zhimo-ui/common/colors.ts
export interface ZhimoSwatch {
  label: string
  value: string
  on: string
  note?: string
  gradient?: string
}

export interface ZhimoColorGroup {
  groupId: string
  groupName: string
  swatches: ZhimoSwatch[]
}

function onColor(bg: string): string {
  if (bg.includes('rgba') || bg.includes('linear-gradient')) return '#FFFFFF'
  const hex = bg.replace('#', '').toUpperCase()
  if (hex.length !== 6) return '#FFFFFF'
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  const y = (r * 299 + g * 587 + b * 114) / 1000
  return y >= 160 ? '#101418' : '#FFFFFF'
}

export const ZhimoColors: ZhimoColorGroup[] = [
  {
    groupId: 'brand',
    groupName: '品牌色系',
    swatches: [
      { label: 'Zhimo Blue', value: '#465CFF', on: onColor('#465CFF'), note: '默认主色' },
      { label: 'Blue Light', value: '#8F9BFF', on: onColor('#8F9BFF') },
      { label: 'Blue Dark',  value: '#2B3FFF', on: onColor('#2B3FFF') },
      { label: 'Indigo',     value: '#3D5AFE', on: onColor('#3D5AFE') },
      { label: 'Violet',     value: '#8A3FFC', on: onColor('#8A3FFC') },
      { label: 'Grape',      value: '#5B2EFF', on: onColor('#5B2EFF') },
      { label: 'Pink',       value: '#FF3D8D', on: onColor('#FF3D8D') },
      { label: 'Orange',     value: '#FF7A00', on: onColor('#FF7A00') },
      { label: 'Teal',       value: '#12B5A6', on: onColor('#12B5A6') },
      { label: 'Cyan',       value: '#00D4FF', on: onColor('#00D4FF') },
      { label: 'Lime',       value: '#8BD300', on: onColor('#8BD300') },
      { label: 'Brown',      value: '#8B5E34', on: onColor('#8B5E34') }
    ]
  },
  {
    groupId: 'status',
    groupName: '状态色',
    swatches: [
      { label: 'Success', value: '#09BE4F', on: onColor('#09BE4F') },
      { label: 'Warning', value: '#FFB703', on: onColor('#FFB703') },
      { label: 'Danger',  value: '#FF2B2B', on: onColor('#FF2B2B') },
      { label: 'Info',    value: '#00B8D9', on: onColor('#00B8D9') }
    ]
  },
  {
    groupId: 'neutral',
    groupName: '中性色阶',
    swatches: [
      { label: 'N0',   value: '#FFFFFF', on: onColor('#FFFFFF') },
      { label: 'N50',  value: '#FAFBFC', on: onColor('#FAFBFC') },
      { label: 'N100', value: '#F4F6F8', on: onColor('#F4F6F8') },
      { label: 'N200', value: '#E8EDF2', on: onColor('#E8EDF2') },
      { label: 'N300', value: '#D9E0E7', on: onColor('#D9E0E7') },
      { label: 'N400', value: '#B8C4D0', on: onColor('#B8C4D0') },
      { label: 'N500', value: '#8A99A8', on: onColor('#8A99A8') },
      { label: 'N600', value: '#5D6B78', on: onColor('#5D6B78') },
      { label: 'N700', value: '#3D4852', on: onColor('#3D4852') },
      { label: 'N800', value: '#232B33', on: onColor('#232B33') },
      { label: 'N900', value: '#101418', on: onColor('#101418') }
    ]
  },
  {
    groupId: 'surface',
    groupName: '背景与容器',
    swatches: [
      { label: 'Surface',    value: '#FAFBFC', on: onColor('#FAFBFC') },
      { label: 'Surface 2',  value: '#F4F6F8', on: onColor('#F4F6F8') },
      { label: 'Elevated',   value: '#FFFFFF', on: onColor('#FFFFFF') },
      { label: 'Primary 6%', value: 'rgba(70, 92, 255, .06)', on: '#101418' },
      { label: 'Danger 6%',  value: 'rgba(255, 43, 43, .06)', on: '#101418' },
      { label: 'Warning 10%',value: 'rgba(255, 183, 3, .10)', on: '#101418' },
      { label: 'Success 6%', value: 'rgba(9, 190, 79, .06)',  on: '#101418' }
    ]
  },
  {
    groupId: 'border',
    groupName: '边界与分割',
    swatches: [
      { label: 'Border',        value: 'rgba(16,20,24,.08)', on: '#FFFFFF' },
      { label: 'Border Strong', value: 'rgba(16,20,24,.16)', on: '#FFFFFF' },
      { label: 'Divider',       value: 'rgba(16,20,24,.06)', on: '#FFFFFF' },
      { label: 'Outline',       value: '#E8EDF2', on: onColor('#E8EDF2') }
    ]
  },
  {
    groupId: 'overlay',
    groupName: '遮罩透明度',
    swatches: [
      { label: 'Mask 10%', value: 'rgba(0,0,0,.10)', on: '#FFFFFF' },
      { label: 'Mask 20%', value: 'rgba(0,0,0,.20)', on: '#FFFFFF' },
      { label: 'Mask 40%', value: 'rgba(0,0,0,.40)', on: '#FFFFFF' },
      { label: 'Mask 60%', value: 'rgba(0,0,0,.60)', on: '#FFFFFF' }
    ]
  },
  {
    groupId: 'gradients',
    groupName: '渐变方案',
    swatches: [
      { label: 'Blue → Violet', value: '#465CFF / #8A3FFC', on: '#FFFFFF', gradient: 'linear-gradient(90deg, #465CFF 0%, #8A3FFC 100%)' },
      { label: 'Pink → Orange', value: '#FF3D8D / #FF7A00', on: '#FFFFFF', gradient: 'linear-gradient(90deg, #FF3D8D 0%, #FF7A00 100%)' },
      { label: 'Teal → Cyan', value: '#12B5A6 / #00D4FF', on: '#FFFFFF', gradient: 'linear-gradient(90deg, #12B5A6 0%, #00D4FF 100%)' },
      { label: 'Danger Soft', value: '#FF8A8A / #FF2B2B', on: '#FFFFFF', gradient: 'linear-gradient(90deg, #FF8A8A 0%, #FF2B2B 100%)' },
      { label: 'Lime → Green', value: '#8BD300 / #09BE4F', on: '#101418', gradient: 'linear-gradient(90deg, #8BD300 0%, #09BE4F 100%)' },
      { label: 'Amber → Orange', value: '#FFB703 / #FF7A00', on: '#101418', gradient: 'linear-gradient(90deg, #FFB703 0%, #FF7A00 100%)' }
    ]
  }
]
