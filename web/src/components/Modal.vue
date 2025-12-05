<script setup>
import { onMounted, onUnmounted, watch, defineProps, defineEmits } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md', // 'sm' | 'md' | 'lg' | 'xl' | 'full'
    validator: (value) => ['sm', 'md', 'lg', 'xl', 'full'].includes(value)
  },
  closeable: {
    type: Boolean,
    default: true
  },
  showFooter: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'confirm'])

const handleKeyDown = (event) => {
  if (event.key === 'Escape' && props.closeable) {
    emit('close')
  }
}

const handleBackdropClick = (event) => {
  if (event.target === event.currentTarget && props.closeable) {
    emit('close')
  }
}

const getSizeClass = () => {
  switch (props.size) {
    case 'sm': return 'max-w-sm'
    case 'md': return 'max-w-lg'
    case 'lg': return 'max-w-2xl'
    case 'xl': return 'max-w-4xl'
    case 'full': return 'max-w-[90vw] max-h-[90vh]'
    default: return 'max-w-lg'
  }
}

watch(() => props.show, (newValue) => {
  if (newValue) {
    document.addEventListener('keydown', handleKeyDown)
  } else {
    document.removeEventListener('keydown', handleKeyDown)
  }
})

onMounted(() => {
  if (props.show) {
    document.addEventListener('keydown', handleKeyDown)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <Teleport to="body">
    <div 
      v-if="show" 
      class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      @click="handleBackdropClick"
    >
      <div :class="['w-full rounded-lg border bg-card p-6 shadow-lg', getSizeClass()]">
        <!-- Header -->
        <div v-if="title || $slots.header" class="flex items-center justify-between mb-4">
          <slot name="header">
            <h3 class="text-lg font-semibold">{{ title }}</h3>
          </slot>
          <button 
            v-if="closeable" 
            @click="emit('close')" 
            class="p-1 hover:bg-accent rounded-md"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <slot></slot>
        </div>

        <!-- Footer -->
        <div v-if="showFooter && $slots.footer" class="flex justify-end space-x-2 pt-4 border-t mt-4">
          <slot name="footer"></slot>
        </div>
      </div>
    </div>
  </Teleport>
</template>
