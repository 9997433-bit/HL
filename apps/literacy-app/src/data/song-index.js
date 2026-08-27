/**
 * 儿歌语料的「轻」索引。
 *
 * 和 poem-index.js 同样的理由：首页学习地图只想在卡片上写「唱过 2 / 7」，
 * 为这一个数字把整份 songs.js（七首歌的逐字拼音和曲谱）拉进首页分块不划算。
 *
 * 这个数字必须和 SONGS.length 一致，`npm run check:data` 会核对。
 */

export const TOTAL_SONGS = 7
