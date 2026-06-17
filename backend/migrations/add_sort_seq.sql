-- 给 trips 表加上自增排序列，替代 updated_at 做可靠插入顺序排序
-- 执行: psql -U smartjourney -d smartjourney -f add_sort_seq.sql

BEGIN;

-- 1. 添加 BIGSERIAL 列（自动创建 SEQUENCE + 默认值）
ALTER TABLE trips ADD COLUMN sort_seq BIGSERIAL;

-- 2. 回填已有行：按 created_at 顺序分配序号
--    因为 BIGSERIAL 的默认值只在 INSERT 时生效，已有行的值由 SEQUENCE 分配
--    这里手动按 created_at 升序重新编号，确保旧数据也按创建顺序排列
WITH ordered AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at ASC, id ASC) AS rn
    FROM trips
)
UPDATE trips t SET sort_seq = o.rn
FROM ordered o WHERE t.id = o.id;

-- 3. 将 SEQUENCE 跳到当前最大值之后（避免新插入的值与回填值冲突）
SELECT setval(
    pg_get_serial_sequence('trips', 'sort_seq'),
    (SELECT COALESCE(MAX(sort_seq), 0) FROM trips)
);

-- 4. 创建索引（DESC，因为列表查询是 ORDER BY sort_seq DESC）
CREATE INDEX ix_trips_sort_seq_desc ON trips (sort_seq DESC);

-- 5. 注释
COMMENT ON COLUMN trips.sort_seq IS '自增排序序号（BIGSERIAL），替代 updated_at 做可靠的插入顺序排序';

COMMIT;
