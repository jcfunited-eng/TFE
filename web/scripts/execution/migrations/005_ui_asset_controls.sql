-- Migration 005: Market Condition Banner CMS
-- Creates ui_asset_controls table for dynamic hero ribbon on the Recommendations page.
-- Each row maps a SPY D_k state (-1, 0, +1) to a background image, instructional text, and text color.

CREATE TABLE IF NOT EXISTS ui_asset_controls (
  id                     SERIAL PRIMARY KEY,
  condition_key          VARCHAR(64)  NOT NULL UNIQUE,
  background_image_path  VARCHAR(512) NOT NULL DEFAULT '',
  instructional_text     TEXT         NOT NULL DEFAULT '',
  text_color_hex         VARCHAR(16)  NOT NULL DEFAULT '#FFFFFF',
  updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Seed the three D_k states
INSERT INTO ui_asset_controls (condition_key, background_image_path, instructional_text, text_color_hex)
VALUES
  ('D_k_minus_1', '', 'CONDITIONS LOOK BAD; TALK TO YOUR BROKER ABOUT AVOIDING PURCHASES.',              '#FFFFFF'),
  ('D_k_0',       '', 'CONDITIONS LOOK MIXED SO BE SURE TO TALK OVER ALL DECISIONS WITH YOUR BROKER.',   '#FFFFFF'),
  ('D_k_plus_1',  '', 'CONDITIONS LOOK FAVORABLE — TALK TO YOUR BROKER ABOUT MAKING PURCHASES NOW. RISKS ARE LOW.', '#FFFFFF')
ON CONFLICT (condition_key) DO NOTHING;
