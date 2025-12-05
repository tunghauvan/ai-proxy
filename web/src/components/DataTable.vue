<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true
    // Each column: { key: string, label: string, align?: 'left' | 'center' | 'right', class?: string }
  },
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  emptyMessage: {
    type: String,
    default: 'No data found'
  },
  clickable: {
    type: Boolean,
    default: true
  },
  rowKey: {
    type: String,
    default: 'id'
  }
})

const emit = defineEmits(['row-click'])

const handleRowClick = (row) => {
  if (props.clickable) {
    emit('row-click', row)
  }
}

const getAlignClass = (align) => {
  switch (align) {
    case 'right': return 'text-right'
    case 'center': return 'text-center'
    default: return 'text-left'
  }
}
</script>

<template>
  <div class="rounded-md border bg-card">
    <div class="relative w-full overflow-auto">
      <table class="w-full caption-bottom text-sm">
        <thead class="[&_tr]:border-b">
          <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
            <th 
              v-for="col in columns" 
              :key="col.key"
              :class="[
                'h-8 px-3 align-middle font-medium text-muted-foreground',
                getAlignClass(col.align),
                col.class
              ]"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="[&_tr:last-child]:border-0">
          <tr v-if="loading">
            <td :colspan="columns.length" class="px-3 py-2 text-center">Loading...</td>
          </tr>
          <tr v-else-if="data.length === 0">
            <td :colspan="columns.length" class="px-3 py-2 text-center">{{ emptyMessage }}</td>
          </tr>
          <tr 
            v-else 
            v-for="row in data" 
            :key="row[rowKey]" 
            :class="[
              'border-b transition-colors hover:bg-muted/50',
              clickable ? 'cursor-pointer' : ''
            ]"
            @click="handleRowClick(row)"
          >
            <slot name="row" :row="row" :columns="columns">
              <td 
                v-for="col in columns" 
                :key="col.key"
                :class="[
                  'px-3 py-2 align-middle',
                  getAlignClass(col.align),
                  col.class
                ]"
              >
                <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                  {{ row[col.key] }}
                </slot>
              </td>
            </slot>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
