<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    // 'default' | 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost'
    validator: (value) => ['default', 'primary', 'secondary', 'destructive', 'outline', 'ghost'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'icon'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const getButtonClass = () => {
  const base = 'inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50'
  
  let variantClass = ''
  switch (props.variant) {
    case 'primary':
      variantClass = 'bg-primary text-primary-foreground hover:bg-primary/90'
      break
    case 'secondary':
      variantClass = 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
      break
    case 'destructive':
      variantClass = 'border border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground'
      break
    case 'outline':
      variantClass = 'border border-input bg-background hover:bg-accent hover:text-accent-foreground'
      break
    case 'ghost':
      variantClass = 'hover:bg-accent hover:text-accent-foreground'
      break
    default:
      variantClass = 'border border-input bg-background hover:bg-accent hover:text-accent-foreground'
  }
  
  let sizeClass = ''
  switch (props.size) {
    case 'sm':
      sizeClass = 'h-8 px-3 py-1'
      break
    case 'lg':
      sizeClass = 'h-11 px-8 py-3'
      break
    case 'icon':
      sizeClass = 'h-9 w-9 p-2'
      break
    default:
      sizeClass = 'h-9 px-4 py-2'
  }
  
  return `${base} ${variantClass} ${sizeClass}`
}
</script>

<template>
  <button :class="getButtonClass()" :disabled="disabled">
    <slot></slot>
  </button>
</template>
