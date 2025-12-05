<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    // 'default' | 'success' | 'warning' | 'error' | 'primary' | 'secondary'
    validator: (value) => ['default', 'success', 'warning', 'error', 'primary', 'secondary'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md'].includes(value)
  }
})

const getVariantClass = () => {
  const base = 'inline-flex items-center rounded-full border font-semibold transition-colors'
  const sizeClass = props.size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs'
  
  switch (props.variant) {
    case 'success':
      return `${base} ${sizeClass} border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100`
    case 'warning':
      return `${base} ${sizeClass} border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100`
    case 'error':
      return `${base} ${sizeClass} border-transparent bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100`
    case 'primary':
      return `${base} ${sizeClass} border-transparent bg-primary/10 text-primary`
    case 'secondary':
      return `${base} ${sizeClass} border-transparent bg-secondary text-secondary-foreground`
    default:
      return `${base} ${sizeClass} border-transparent bg-secondary text-secondary-foreground`
  }
}
</script>

<template>
  <span :class="getVariantClass()">
    <slot></slot>
  </span>
</template>
