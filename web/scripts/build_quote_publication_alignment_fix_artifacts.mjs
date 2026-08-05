#!/usr/bin/env node
import { spawnSync } from 'child_process';

const result = spawnSync('python3', ['web/scripts/build_quote_publication_alignment_fix_artifacts.py'], {
  cwd: '/workspaces/Tao_Financial_Engine',
  stdio: 'inherit',
});

if (result.error) {
  throw result.error;
}

process.exit(result.status ?? 1);
