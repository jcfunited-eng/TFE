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
COPY web/data ./data

RUN npm run build


FROM public.ecr.aws/docker/library/node:22-bookworm-slim AS runtime

ENV NODE_ENV=production
ENV PORT=3000
ENV TFE_PYTHON_BIN=python3
ENV NODE_EXTRA_CA_CERTS=/app/certs/rds-global-bundle.pem
ENV PYTHONPATH=/app:/app/web

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        python3-boto3 \
        python3-cryptography \
        python3-requests \
        python3-numpy \
        python3-pandas \
        python3-dotenv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci --omit=dev \
    && npm cache clean --force

COPY --from=builder /app/web/.next ./.next
COPY --from=builder /app/web/public ./public
COPY --from=builder /app/web/scripts ./scripts
COPY --from=builder /app/web/data ./data
COPY web/postcss.config.mjs ./postcss.config.mjs

WORKDIR /app

COPY certs ./certs
COPY ses_core ./ses_core
COPY uf_core ./uf_core
COPY tools/oracle_program ./tools/oracle_program
COPY backups/runtime/oracle_program ./backups/runtime/oracle_program

COPY tfe_ses_core_adapter.py ./tfe_ses_core_adapter.py
COPY aws_root_key_provider.py ./aws_root_key_provider.py

COPY rebuild_uf_snapshot.py ./rebuild_uf_snapshot.py
COPY uf_mdg_snapshot.py ./uf_mdg_snapshot.py
COPY run_refresh_with_l5_learning.py ./run_refresh_with_l5_learning.py
COPY l5_policy_learning_pipeline.py ./l5_policy_learning_pipeline.py
COPY l5_policy_learning_latest.json ./l5_policy_learning_latest.json
COPY pscf_policy_runtime.json ./pscf_policy_runtime.json
COPY real_world_cleaned_universe_l5_row_trace_full.csv ./real_world_cleaned_universe_l5_row_trace_full.csv
COPY unified_market_data_service.py ./unified_market_data_service.py
COPY tfe_market_data.py ./tfe_market_data.py
COPY tfe_market_data_service.py ./tfe_market_data_service.py
COPY tfe_bar_integrity.py ./tfe_bar_integrity.py
COPY tfe_market_data_factory.py ./tfe_market_data_factory.py
COPY massive_market_data_service.py ./massive_market_data_service.py
COPY alpaca_market_data_service.py ./alpaca_market_data_service.py
COPY massive_universe_cache.py ./massive_universe_cache.py
COPY massive_universe_cache_etf.py ./massive_universe_cache_etf.py
COPY massive_universe_index.py ./massive_universe_index.py
COPY massive_universe_crypto.py ./massive_universe_crypto.py

COPY g32_horse_race.py ./g32_horse_race.py
COPY g32_horse_race_mom_irf.py ./g32_horse_race_mom_irf.py
COPY g32_mom_irf_loop_runner.py ./g32_mom_irf_loop_runner.py
COPY g32_horse_race_loop_runner.py ./g32_horse_race_loop_runner.py
COPY overnight_optimizer_manager.py ./overnight_optimizer_manager.py
COPY horse_race_status.py ./horse_race_status.py

COPY uf_snapshot.ses.json ./uf_snapshot.ses.json
COPY uf_snapshot_rebuild_report.json ./uf_snapshot_rebuild_report.json
COPY massive_universe_stocks.json ./massive_universe_stocks.json
COPY massive_universe_etf.json ./massive_universe_etf.json
COPY massive_universe_index.json ./massive_universe_index.json
COPY massive_universe_crypto.json ./massive_universe_crypto.json

COPY backups/strict-ab-frozen-dataset-*.json ./backups/
COPY backups/pscf-policy-anomaly-watch-*.json ./backups/

COPY data ./data
COPY market_data ./market_data

RUN mkdir -p /app/web_user_data/.ses_tmp \
    && chown -R node:node /app

USER node

WORKDIR /app/web

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
