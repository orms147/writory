-- G6 (D-137): bộ phân loại ô tự viết chấm hành động có nằm trong luật của thế giới và sức của nhân vật
-- chính không (`safety.classify.Feasibility`). Lưu cùng hành động để chương sau biết có phải kiểm trang
-- không. NULL: lựa chọn có sẵn (luôn trong luật), hoặc hành động tự viết lưu trước migration này (coi
-- như trong luật). Chỉ hành động tự viết mới có giá trị. Cách chạy: writory.db.migrate (D-20).

ALTER TABLE player_actions
    ADD COLUMN feasibility text
        CHECK (feasibility IN ('within_rules', 'beyond_world_rules', 'beyond_character')),
    ADD CONSTRAINT player_actions_feasibility_custom_only
        CHECK (feasibility IS NULL OR source = 'custom');
