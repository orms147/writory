-- Chi phí ước tính của lời gọi không có usage (G8, D-64): bị huỷ khi người chơi ngắt kết nối,
-- đứt giữa chừng, hay phản hồi thiếu usage.cost. Dòng đó mang chi phí tối đa của lời gọi
-- (`estimated`), để trần mỗi truyện vẫn cộng được; có id generation của OpenRouter thì tra lại
-- và thay bằng số thật (`estimated` thành false). Cách chạy: writory.db.migrate (D-20).

ALTER TABLE llm_costs ADD COLUMN estimated boolean NOT NULL DEFAULT false;
ALTER TABLE llm_costs ADD COLUMN generation_id text;
ALTER TABLE llm_costs ADD CONSTRAINT llm_costs_estimate_has_cost
    CHECK (NOT estimated OR cost_usd IS NOT NULL);

-- Dòng còn chờ tra lại theo id.
CREATE INDEX llm_costs_pending_estimates ON llm_costs (story_id, setup_session_id)
    WHERE estimated AND generation_id IS NOT NULL;
