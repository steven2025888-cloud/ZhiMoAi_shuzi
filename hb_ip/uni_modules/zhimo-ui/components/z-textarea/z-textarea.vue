<template>
  <view class="zta" :class="wrapClass" :style="wrapStyle" @tap="onWrapTap">
    <!-- top divider (list style) -->
    <view
      v-if="!innerBorder && borderTop"
      class="zta__line zta__line--top"
      :style="topLineStyle"
    />
    <view class="zta__row" :class="{ 'zta__row--top': alignTop }">
      <!-- required asterisk -->
      <view v-if="required" class="zta__req" :style="reqStyle"><text class="zta__reqText">*</text></view>

      <!-- label -->
      <view v-if="label" class="zta__label" :style="labelStyle">
        <text class="zta__labelText" :style="labelTextStyle">{{ label }}</text>
      </view>

      <!-- left slot -->
      <view v-if="$slots.left" class="zta__addon zta__addon--left">
        <slot name="left" />
      </view>

      <!-- textarea field -->
      <view class="zta__field">
        <textarea
          class="zta__native"
          :class="nativeClass"
          :style="nativeStyle"
          :name="name"
          :value="inner"
          :placeholder="inner ? '' : placeholder"
          :placeholder-style="resolvedPlaceholderStyle"
          :disabled="disabled"
          :maxlength="maxlength"
          :focus="focusInner"
          :auto-height="autoHeight"
          :fixed="fixed"
          :cursor-spacing="cursorSpacing"
          :show-confirm-bar="showConfirmBar"
          :cursor="cursor"
          :selection-start="selectionStart"
          :selection-end="selectionEnd"
          :adjust-position="adjustPosition"
          :hold-keyboard="holdKeyboard"
          :disable-default-padding="disableDefaultPadding"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
          @confirm="emit('confirm', $event?.detail?.value ?? inner)"
          @linechange="emit('linechange', $event)"
          @keyboardheightchange="emit('keyboardheightchange', $event)"
        />
        <!-- overlay counter inside field -->
        <view v-if="showCount" class="zta__counter" :style="counterWrapStyle">
          <text class="zta__counterText" :style="counterTextStyle">{{ counterText }}</text>
        </view>

        <!-- right default slot (icons, buttons) -->
        <view v-if="$slots.default" class="zta__addon zta__addon--right">
          <slot />
        </view>
      </view>
    </view>

    <!-- bottom divider (list style) -->
    <view
      v-if="!innerBorder && borderBottom"
      class="zta__line zta__line--bottom"
      :style="bottomLineStyle"
    />
  </view>

  <!-- footer: error / help text -->
  <view v-if="errorText || helpText" class="zta__footer">
    <text v-if="errorText" class="zta__error" :style="errorStyle">{{ errorText }}</text>
    <text v-else class="zta__help" :style="helpStyle">{{ helpText }}</text>
  </view>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

/**
 * z-textarea
 * - A lightweight textarea wrapper for uni-app (Vue3)
 * - Supports label/required, list borders, inner border, counter, slots
 */

const props = defineProps({
  // value
  modelValue: { type: [String, Number], default: '' },
  // optional compatibility input
  value: { type: [String, Number], default: '' },

  name: { type: String, default: '' },
  placeholder: { type: String, default: '' },

  disabled: { type: Boolean, default: false },
  disabledStyle: { type: Boolean, default: true },

  // focus control
  focus: { type: Boolean, default: false },

  // native options
  autoHeight: { type: Boolean, default: false },
  fixed: { type: Boolean, default: false },
  cursorSpacing: { type: Number, default: 0 },
  maxlength: { type: [Number, String], default: 500 },
  showConfirmBar: { type: Boolean, default: true },
  cursor: { type: Number, default: -1 },
  selectionStart: { type: Number, default: -1 },
  selectionEnd: { type: Number, default: -1 },
  adjustPosition: { type: Boolean, default: true },
  holdKeyboard: { type: Boolean, default: false },
  disableDefaultPadding: { type: Boolean, default: true },

  // layout
  label: { type: String, default: '' },
  labelWidth: { type: [Number, String], default: 160 },
  labelSize: { type: [Number, String], default: 30 },
  labelColor: { type: String, default: '#333' },
  alignTop: { type: Boolean, default: false },

  required: { type: Boolean, default: false },
  requiredColor: { type: String, default: '#ff3b30' },
  requiredTop: { type: String, default: '34rpx' },

  // style: field box
  bgColor: { type: String, default: '#fff' },
  radius: { type: [Number, String], default: 14 },

  // borders
  innerBorder: { type: Boolean, default: true }, // outline border
  borderColor: { type: String, default: 'rgba(0,0,0,.12)' },
  activeBorderColor: { type: String, default: '#2b7cff' },

  // list borders (when innerBorder=false)
  borderTop: { type: Boolean, default: true },
  borderBottom: { type: Boolean, default: true },
  topInsetLeft: { type: [Number, String], default: 0 },
  topInsetRight: { type: [Number, String], default: 0 },
  bottomInsetLeft: { type: [Number, String], default: 0 },
  bottomInsetRight: { type: [Number, String], default: 0 },

  // padding supports: [v,h] or [t,r,b,l] (rpx)
  padding: { type: Array, default: () => [16, 18] },

  // textarea look
  height: { type: String, default: '200rpx' },
  minHeight: { type: String, default: '30rpx' },
  fontSize: { type: [Number, String], default: 28 },
  textColor: { type: String, default: '#111' },
  textAlign: { type: String, default: 'left' }, // 'left' | 'right'
  trim: { type: Boolean, default: false },

  // placeholder
  placeholderStyle: { type: String, default: '' },
  placeholderColor: { type: String, default: 'rgba(0,0,0,.45)' },
  placeholderOpacity: { type: Number, default: 0.85 },

  // counter
  showCount: { type: Boolean, default: false },
  countColor: { type: String, default: 'rgba(0,0,0,.45)' },
  countSize: { type: [Number, String], default: 22 },

  // footer text
  error: { type: String, default: '' },
  help: { type: String, default: '' },
  errorColor: { type: String, default: '#ff3b30' },
  helpColor: { type: String, default: 'rgba(0,0,0,.55)' },
  footerSize: { type: [Number, String], default: 22 }
})

const emit = defineEmits([
  'update:modelValue',
  'input',
  'change',
  'focus',
  'blur',
  'confirm',
  'click',
  'linechange',
  'keyboardheightchange'
])

function normalizePadding(p) {
  const arr = Array.isArray(p) ? p : []
  if (arr.length >= 4) return [arr[0], arr[1], arr[2], arr[3]]
  if (arr.length === 2) return [arr[0], arr[1], arr[0], arr[1]]
  if (arr.length === 1) return [arr[0], arr[0], arr[0], arr[0]]
  return [0, 0, 0, 0]
}

const isFocused = ref(false)
const focusInner = ref(false)

const inner = ref('')
const pickInitial = () => {
  const mv = props.modelValue
  const v = props.value
  if (mv !== '' && mv != null) return String(mv)
  if (v !== '' && v != null) return String(v)
  return ''
}
inner.value = pickInitial()

watch(() => props.modelValue, (v) => {
  // Do not destroy local state for controlled empty -> keep in sync
  inner.value = v == null ? '' : String(v)
})
watch(() => props.value, (v) => {
  // value is only a fallback for non-v-model usage
  if ((props.modelValue == null || String(props.modelValue) === '') && v != null) {
    inner.value = String(v)
  }
})

watch(() => props.focus, async (v) => {
  await nextTick()
  // small delay improves cross-platform focus behavior
  setTimeout(() => { focusInner.value = !!v }, 20)
}, { immediate: true })

const errorText = computed(() => props.error || '')
const helpText = computed(() => (errorText.value ? '' : (props.help || '')))

const wrapClass = computed(() => ({
  'is-disabled': props.disabled,
  'is-error': !!errorText.value,
  'is-focused': isFocused.value,
  'is-list': !props.innerBorder
}))

const pad = computed(() => normalizePadding(props.padding))

const wrapStyle = computed(() => {
  const [pt, pr, pb, pl] = pad.value
  const borderClr = isFocused.value ? props.activeBorderColor : props.borderColor
  return {
    background: props.bgColor,
    borderRadius: `${Number(props.radius)}rpx`,
    paddingTop: `${pt}rpx`,
    paddingRight: `${pr}rpx`,
    paddingBottom: `${pb}rpx`,
    paddingLeft: `${pl}rpx`,
    borderWidth: props.innerBorder ? '1px' : '0px',
    borderStyle: 'solid',
    borderColor: props.innerBorder ? borderClr : 'transparent'
  }
})

const topLineStyle = computed(() => ({
  background: props.borderColor || 'rgba(0,0,0,.10)',
  left: `${Number(props.topInsetLeft)}rpx`,
  right: `${Number(props.topInsetRight)}rpx`
}))

const bottomLineStyle = computed(() => ({
  background: props.borderColor || 'rgba(0,0,0,.10)',
  left: `${Number(props.bottomInsetLeft)}rpx`,
  right: `${Number(props.bottomInsetRight)}rpx`
}))

const labelStyle = computed(() => ({ minWidth: `${Number(props.labelWidth)}rpx` }))
const labelTextStyle = computed(() => ({ fontSize: `${Number(props.labelSize)}rpx`, color: props.labelColor }))

const reqStyle = computed(() => ({
  top: props.alignTop ? props.requiredTop : '50%',
  color: props.requiredColor
}))

const resolvedPlaceholderStyle = computed(() => {
  if (props.placeholderStyle && props.placeholderStyle.trim().length > 0) return props.placeholderStyle
  return `color:${props.placeholderColor};opacity:${props.placeholderOpacity};`
})

const nativeStyle = computed(() => ({
  height: props.height,
  minHeight: props.minHeight,
  fontSize: `${Number(props.fontSize)}rpx`,
  color: props.textColor,
  textAlign: props.textAlign === 'right' ? 'right' : 'left',
  paddingRight: props.showCount ? '86rpx' : '0rpx'
}))

const nativeClass = computed(() => ({
  'zta__native--disabled': props.disabled && props.disabledStyle
}))

const counterText = computed(() => {
  const len = String(inner.value || '').length
  const max = Number(props.maxlength)
  if (max < 0) return `${len}`
  return `${len}/${max}`
})

const counterWrapStyle = computed(() => ({
  opacity: props.disabled ? 0.55 : 1
}))
const counterTextStyle = computed(() => ({
  fontSize: `${Number(props.countSize)}rpx`,
  color: props.countColor
}))

const errorStyle = computed(() => ({
  fontSize: `${Number(props.footerSize)}rpx`,
  color: props.errorColor
}))
const helpStyle = computed(() => ({
  fontSize: `${Number(props.footerSize)}rpx`,
  color: props.helpColor
}))

function onWrapTap() {
  emit('click')
}

function handleFocus(e) {
  isFocused.value = true
  emit('focus', e)
}
function handleBlur(e) {
  isFocused.value = false
  emit('blur', e)
}

function handleInput(e) {
  let v = e?.detail?.value ?? ''
  if (props.trim) v = String(v).trim()
  inner.value = v
  emit('update:modelValue', v)
  emit('input', v)
  emit('change', v)
}
</script>

<style scoped>
/* root wrapper */
.zta{
  width: 100%;
  box-sizing: border-box;
  position: relative;
}
.zta.is-disabled{ opacity: .75; }
.zta.is-error{ }
.zta.is-focused{ }

/* list divider lines */
.zta__line{
  position:absolute;
  height: 1px;
  transform: scaleY(.5);
}
.zta__line--top{ top: 0; }
.zta__line--bottom{ bottom: 0; }

/* row layout */
.zta__row{
  display:flex;
  align-items:center;
  gap: 12rpx;
}
.zta__row--top{ align-items:flex-start; }

/* required */
.zta__req{
  width: 18rpx;
  position: relative;
}
.zta__reqText{
  position:absolute;
  left:0;
  transform: translateY(-50%);
  font-size: 26rpx;
  line-height: 1;
}

/* label */
.zta__label{ flex-shrink:0; }
.zta__labelText{ line-height: 1.2; }

/* addons */
.zta__addon{ flex-shrink:0; display:flex; align-items:center; }
.zta__addon--left{ margin-right: 4rpx; }
.zta__addon--right{ margin-left: 6rpx; }

/* field */
.zta__field{
  position: relative;
  flex:1;
  display:flex;
  align-items:flex-start;
}
.zta__native{
  width:100%;
  box-sizing:border-box;
  line-height: 1.35;
}
.zta__native--disabled{ opacity: .85; }

/* counter overlay */
.zta__counter{
  position:absolute;
  right: 8rpx;
  bottom: 6rpx;
  padding: 6rpx 8rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,.03);
}
.zta__counterText{
  line-height: 1;
}

/* footer */
.zta__footer{
  margin-top: 10rpx;
  padding: 0 6rpx;
}
.zta__error, .zta__help{
  line-height: 1.35;
}
</style>