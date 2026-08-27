/**
 * 玩法侧读取年龄档的统一入口。
 *
 * 返回当前档位的完整配置（data/age-band.js 里的那张表）。
 * 传了 onChange，家长在另一个标签页/家长中心改档后，本页会立刻按新档位重开一轮，
 * 不用等孩子退出去再进来。
 */
import { computed, watch } from 'vue'
import { bandOf } from '@/data/age-band.js'
import { useSettingsStore } from '@/stores/settings.js'

export function useAgeBand(onChange) {
  const settings = useSettingsStore()
  const band = computed(() => bandOf(settings.ageBand))
  if (onChange) watch(() => settings.ageBand, () => onChange(band.value))
  return band
}
