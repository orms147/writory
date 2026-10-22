-- Token vào được đọc từ cache prompt của nhà cung cấp (usage.prompt_tokens_details.cached_tokens,
-- D-96). NULL: phản hồi không báo hoặc dòng cũ; 0: đã báo, không có cache. Không ảnh hưởng chi phí:
-- cost_usd vẫn là số OpenRouter tính. Cách chạy: writory.db.migrate (D-20).

ALTER TABLE llm_costs ADD COLUMN cached_tokens integer CHECK (cached_tokens >= 0);
