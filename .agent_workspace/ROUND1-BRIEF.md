# Round 1 结论简报（注入 Round 2 全部子代理）

## 已实现功能
### 识字 App (literacy-app)
- 40字/4单元、3绘本16页、8成语、14偏旁、听音识字、笔顺离线(133字JSON 256KB)
- 10路由全通、Pinia进度、家长面板、三主题护眼、check:data + smoke 17路由+6交互
- FSRS-lite 契约在 `src/utils/srs.js`，**尚未接线**到复习队列

### 数学 App (math-app)
- 7模块视图全通：数感/计算/几何/逻辑/数独/应用题/成就
- 16应用题母题、4×4数独、掌握度模型、Tone.js音效
- check:content + smoke 9路由+10交互

### 基础设施
- dist/hongen-literacy-app.zip (~272KB)、dist/hongen-math-app.zip (~149KB)
- shared/design-tokens.css、ui-ux-design-spec、sota-acceptance-criteria
- scripts/setup|build-all|test-*|benchmark|stress-test|verify-resources

## 遗留缺陷
1. **双App并行死代码**：literacy `HomeMap/Books.vue` 等；math `core/engine/*` + `src/views/*` 未引用
2. **数独/应用题/生成器各两套实现**，需收敛到一套
3. **Tone.js 主包 431KB gzip 138KB**，可换轻量 WebAudio
4. **FSRS 未接线**；字库仅40字 demo 规模
5. **TTS 依赖系统语音**，无中文嗓音时静默失败
6. **成语 hero 卡片不跟随主题**；绘本无解锁拦截
7. **无 Service Worker**；无 Lighthouse/axe 自动化
8. **冒烟测试部分断言曾假阳性**（已修），判分正确性靠 check:content 非 E2E

## 性能瓶颈
- 大量汉字渲染需分页/虚拟滚动（stress-test 已测 2.55MiB HTML）
- Web Audio 首次需用户手势解锁
- hanzi-writer-data devDep 47MB（产物仅256KB）

## Round 2 攻坚重点（P0）
1. 代码归并：删除/合并双套 views 与 engines
2. FSRS 接线 + 字库扩至 100+ 字
3. 设计令牌迁移（literacy theme.css → shared/design-tokens.css）
4. QuizShell 通用答题壳（math）
5. 验收自动化脚本（Lighthouse/axe 阈值）
6. Service Worker 离线预缓存
7. 听音识字换皮 + 绘本逐句朗读高亮
8. Tone.js → 轻量 WebAudio 瘦身（可选 P1）

## SOTA 验收差距（摘自 sota-acceptance-criteria.md）
- 识字200字、数学7类完整玩法、Lighthouse≥95、首屏JS<250KB gzip、axe零critical、断网全功能
