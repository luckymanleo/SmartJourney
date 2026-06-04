# 城市选择器 — 最终实现

> 2026-06-03 | CityCascader + location_service

## 需求

- 省市区三级联动选择
- 拼音/首字母/汉字搜索
- 半屏弹出，宽度与 App 主体一致 (max-w-md)
- 省份按拼音字母分组排序

## 方案

**数据源**：`eduosi/district` (GitHub 5.4k stars)
- 格式：CSV (3433行)
- 字段：id, name, parent_id, initial, initials, pinyin, suffix, code, area_code
- 数据来源：民政部全国行政区划信息查询平台
- 更新：CHANGES 文件追踪历次调整

**无外部依赖**：拼音已在 CSV 中，无需 pypinyin。

## 后端 API

| 端点 | 参数 | 返回 |
|------|------|------|
| `GET /api/v1/info/locations` | `pid` (父级ID，0=省) | 子级列表 (按拼音排序) |
| `GET /api/v1/info/locations/search` | `keyword`, `limit` | 拼音/汉字搜索 |

### 数据加载

`location_service.py` 启动时一次性加载 CSV 到内存：
- `_children: dict[int, list]` — parent_id → children 索引
- `_flat_search: list` — 扁平搜索列表 (市/区 + 省级实体)
- 排序：`get_children()` 按拼音字母排序

### 搜索匹配

支持三种匹配方式：
```
汉字:    "杭州" → 精确匹配/前缀/包含
全拼:    "hangzhou" → 精确匹配/前缀
首字母:  "hz" → 精确匹配 (惠州、杭州、汉中、湖州、菏泽、贺州)
```

省级实体也加入搜索索引（省/直辖市/自治区/特别行政区均可搜）。

## 前端组件

`CityCascader.tsx` — 底部半屏弹窗：

```
┌─────────────────────────────────┐
│ ← 选择城市                  ✕  │  ← Header: 返回 + 标题 + 关闭
│ 🔍 搜索（拼音/首字母/汉字）    │  ← 搜索框 (200ms 防抖)
├─────────────────────────────────┤
│ A                               │
│ [安徽] [澳门]                   │  ← 省份按首字母分组 chips
│ B                               │
│ [北京]                          │
│ C                               │
│ [重庆]                          │
│ ...                             │
└─────────────────────────────────┘

点击省份 → 城市列表 (带拼音)
点击城市 → 填入并关闭 (或展开区县)
```

### 关键参数

- `max-w-md`：宽度 448px，与 App Layout 一致
- `max-h-[55vh]`：最大高度 55% 视口
- `autoFocus`：打开时搜索框自动聚焦
- 首字母分组：`useMemo` 按 `initial.toUpperCase()` 分组
- 搜索防抖：200ms `setTimeout`

### 交互流程

```
省份列表 (默认)
  ├─ 点击省份 → 加载城市列表
  │   ├─ 点击城市 → onSelect(name) + onClose
  │   └─ ← 返回 → 回到省份列表
  └─ 搜索框输入 → 实时搜索 (拼音/汉字)
      └─ 点击结果 → onSelect(name) + onClose
```

### 与 SearchPage 集成

```tsx
{showFromPicker && (
  <CityCascader
    value={needsCity ? city : from}
    onSelect={c => { needsCity ? setCity(c) : setFrom(c); setShowFromPicker(false) }}
    onClose={() => setShowFromPicker(false)}
  />
)}
```

旧 CityPicker (55城市手工分组) 已移除，替换为 CityCascader (3433条民政部数据+拼音搜索)。

## 数据统计

- 35 省/直辖市/自治区/特别行政区
- ~340 地级市
- ~3000 区/县
- 合计 3433 条记录
