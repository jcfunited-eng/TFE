FROM public.ecr.aws/docker/library/node:22-bookworm-slim AS deps

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci


FROM public.ecr.aws/docker/library/node:22-bookworm-slim AS builder

WORKDIR /app/web

COPY --from=deps /app/web/node_modules ./node_modules
COPY web/package.json web/package-lock.json ./
COPY web/next.config.ts web/tsconfig.json web/next-env.d.ts web/postcss.config.mjs ./
COPY web/src ./src
COPY web/public ./public
COPY web/scripts ./scripts
RUN mkdir -p ./data
COPY web/data/ui-config.json ./data/ui-config.json
COPY web/data/screener-finviz-overview-cache.json ./data/screener-finviz-overview-cache.json
COPY web/data/screener-profile-overrides.json ./data/screener-profile-overrides.json
COPY web/data/screener-quote-cache.json ./data/screener-quote-cache.json
COPY web/data/screener-quote-cache.failures.json ./data/screener-quote-cache.failures.json
COPY web/data/recommendation-quality-latest.json ./data/recommendation-quality-latest.json

RUN npm run build


FROM public.ecr.aws/docker/library/node:22-bookworm-slim AS runtime

ARG TFE_GIT_COMMIT_SHA=""

LABEL org.opencontainers.image.revision="${TFE_GIT_COMMIT_SHA}"

ENV NODE_ENV=production
ENV PORT=3000
ENV TFE_PYTHON_BIN=python3
ENV NODE_EXTRA_CA_CERTS=/app/certs/rds-global-bundle.pem
ENV PYTHONPATH=/app:/app/web
ENV TFE_IMAGE_GIT_COMMIT_SHA="${TFE_GIT_COMMIT_SHA}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        postgresql-client \
        python3 \
        python3-bs4 \
        python3-boto3 \
        python3-cryptography \
        python3-requests \
        python3-numpy \
        python3-pandas \
        python3-dotenv \
        python3-psycopg2 \
        python3-pip \
    && python3 -m pip install --no-cache-dir --break-system-packages yfinance \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci --omit=dev \
    && npm cache clean --force

COPY --from=builder /app/web/.next ./.next
COPY --from=builder /app/web/public ./public
COPY --from=builder /app/web/scripts ./scripts
RUN mkdir -p ./data
COPY --from=builder /app/web/data/ui-config.json ./data/ui-config.json
COPY --from=builder /app/web/data/screener-finviz-overview-cache.json ./data/screener-finviz-overview-cache.json
COPY --from=builder /app/web/data/screener-profile-overrides.json ./data/screener-profile-overrides.json
COPY --from=builder /app/web/data/screener-quote-cache.json ./data/screener-quote-cache.json
COPY --from=builder /app/web/data/screener-quote-cache.failures.json ./data/screener-quote-cache.failures.json
COPY --from=builder /app/web/data/recommendation-quality-latest.json ./data/recommendation-quality-latest.json
COPY web/postcss.config.mjs ./postcss.config.mjs

WORKDIR /app

COPY certs ./certs
COPY ses_core ./ses_core
COPY uf_core ./uf_core
COPY tools/l0_phase1_sync_postgres.py ./tools/l0_phase1_sync_postgres.py
COPY tools/l0_phase2_bars_sync_postgres.py ./tools/l0_phase2_bars_sync_postgres.py
COPY tools/l1_phase1_sync_postgres.py ./tools/l1_phase1_sync_postgres.py
COPY tools/l2_phase1_sync_postgres.py ./tools/l2_phase1_sync_postgres.py
COPY tools/l3_phase1_sync_postgres.py ./tools/l3_phase1_sync_postgres.py
COPY tools/l4_phase1_decision_sync_postgres.py ./tools/l4_phase1_decision_sync_postgres.py
COPY tools/l4_phase2_structural_snapshot_sync_postgres.py ./tools/l4_phase2_structural_snapshot_sync_postgres.py
COPY tools/l5_db_native_preflight.py ./tools/l5_db_native_preflight.py
COPY tools/l5_phase2_sync_postgres.py ./tools/l5_phase2_sync_postgres.py
COPY tools/evaluate_recommendation_policy_snapshot.py ./tools/evaluate_recommendation_policy_snapshot.py
COPY tools/cp2_quality_audit.py ./tools/cp2_quality_audit.py
COPY tools/backfill_accumulate_fundamentals.py ./tools/backfill_accumulate_fundamentals.py
COPY backups/runtime/recommendation-quality-audit-lane-* ./backups/runtime/
COPY --from=builder /app/web/data/recommendation-quality-latest.json ./web/data/recommendation-quality-latest.json

COPY tfe_ses_core_adapter.py ./tfe_ses_core_adapter.py
COPY aws_root_key_provider.py ./aws_root_key_provider.py
COPY tfe_fundamental_fetcher.py ./tfe_fundamental_fetcher.py

COPY rebuild_uf_snapshot.py ./rebuild_uf_snapshot.py
COPY uf_mdg_snapshot.py ./uf_mdg_snapshot.py
COPY structural_recency_snapshot.py ./structural_recency_snapshot.py
COPY run_refresh_with_l5_learning.py ./run_refresh_with_l5_learning.py
COPY tfe_l5_baseline.py ./tfe_l5_baseline.py
COPY structural_episodes.csv ./structural_episodes.csv
COPY uf_structural_cache.json ./uf_structural_cache.json
COPY unified_market_data_service.py ./unified_market_data_service.py
COPY tfe_market_data.py ./tfe_market_data.py
COPY tfe_market_data_service.py ./tfe_market_data_service.py
COPY tfe_bar_integrity.py ./tfe_bar_integrity.py
COPY tfe_market_data_factory.py ./tfe_market_data_factory.py
COPY massive_market_data_service.py ./massive_market_data_service.py
COPY alpaca_market_data_service.py ./alpaca_market_data_service.py
COPY yahoo_index_market_data_service.py ./yahoo_index_market_data_service.py
COPY massive_universe_cache.py ./massive_universe_cache.py
COPY massive_universe_cache_etf.py ./massive_universe_cache_etf.py
COPY massive_universe_index.py ./massive_universe_index.py
COPY massive_universe_crypto.py ./massive_universe_crypto.py
COPY tfe_deploy_metadata.json ./tfe_deploy_metadata.json

COPY massive_universe_stocks.json ./massive_universe_stocks.json
COPY massive_universe_etf.json ./massive_universe_etf.json
COPY massive_universe_index.json ./massive_universe_index.json
COPY massive_universe_crypto.json ./massive_universe_crypto.json

COPY data ./data
COPY market_data ./market_data

COPY tfe_data_normalizer.py ./tfe_data_normalizer.py
COPY tfe_snapshot_restore.py ./tfe_snapshot_restore.py
COPY tfe_startup.sh ./tfe_startup.sh

RUN mkdir -p /app/web_user_data/.ses_tmp \
    && mkdir -p /app/web/data \
    && chmod +x /app/tfe_startup.sh \
    && chown -R node:node /app

USER node

WORKDIR /app/web

EXPOSE 3000

CMD ["/app/tfe_startup.sh"]
