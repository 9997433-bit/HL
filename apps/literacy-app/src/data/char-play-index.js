/**
 * Play 自动补齐索引 —— 由 apps/literacy-app/scripts/gen-char-play.mjs 生成，请勿手改。
 *
 * 架构岗（r15-arch-contracts）先放一份空索引占位：`char-play.js` 在这里查不到
 * 条目时，会用与生成器完全相同的规则在运行时合成（source: 'runtime'），
 * 所以空索引不会造成任何空洞，调用方也拿不到 null。
 *
 * autofill 岗（r15-play-autofill）跑过生成器后，本文件会被整体覆盖成
 * 1820 字的补齐条目（source: 'generated'，templateFallback: true）。
 * 生成器契约见 .agent_workspace/round15-architecture.md 第 6 节。
 *
 * @type {Record<string, import('./char-play.js').CharPlay>}
 */
export const GENERATED_PLAY = {}
