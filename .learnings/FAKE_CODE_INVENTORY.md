# ⚠️ 伪代码警告清单
# 生成时间: 2026-03-24
# 这些文件被检测为伪代码 - 请勿信任其AI功能

## 🔴 严重伪代码（必须修复）

### second-brain-processor
- [ ] daily_complete_report.py - FAKE_AI_FUNCTION
- [ ] verify_send_link.py - FAKE_AI_FUNCTION  
- [ ] step3_organize_remainder.py - FAKE_AI_FUNCTION
- [ ] article_handler.py - FAKE_AI_FUNCTION x2

### multi-agent-pipeline（几乎全假）
- [ ] layer0/ai_client.py - FAKE_AI_FUNCTION x2
- [ ] layer1/priority_manager.py - FAKE_AI_FUNCTION x2
- [ ] layer1/task_queue.py - FAKE_AI_FUNCTION
- [ ] layer2/estimator.py - FAKE_AI_FUNCTION
- [ ] layer2/planner.py - FAKE_AI_FUNCTION x2 + DOC_DECEPTION x2
- [ ] scripts/start_worker.py - FAKE_AI_FUNCTION
- [ ] scripts/start_scheduler.py - FAKE_AI_FUNCTION
- [ ] scripts/orchestrator_cli.py - FAKE_AI_FUNCTION

### meeting-prep-orchestrator
- [ ] scripts/prep_check.py - FAKE_AI_FUNCTION
- [ ] scripts/topic_discussion_igniter.py - FAKE_AI_FUNCTION
- [ ] scripts/topic_igniter_simple.py - FAKE_AI_FUNCTION

### 其他Skills
- [ ] nano-banana-pro-apiyi/generate_image.py
- [ ] openclaw-version-adapter/scripts/check_version.py - DOC_DECEPTION
- [ ] openclaw-version-adapter/scripts/generate_migration.py
- [ ] knowledge-studio/scripts/knowledge_engine.py
- [ ] cron-health-dashboard/scripts/cron_health_check.py - DOC_DECEPTION
- [ ] auto-compact-dynamic/scripts/dynamic_compactor.py
- [ ] feishu-deduplication/scripts/*.py (2个文件)
- [ ] git-safety-guardian/scripts/git_safety_check.py
- [ ] pipeline-health-monitor/scripts/health_check.py
- [ ] auto-fix/scripts/*.py (2个文件)
- [ ] auto-error-logger/scripts/auto_error_logger.py
- [ ] feishu-send-guardian/scripts/*.py (2个文件)

## ✅ 已修复
- [x] step1_identify_essence.py - 2026-03-24 修复，真正调用API

## 修复优先级
1. P0: second-brain-processor（核心功能）
2. P1: multi-agent-pipeline（大量伪代码）
3. P2: 其他skills

## 修复标准
每个文件修复时必须：
1. 真正调用AI API
2. 通过 user_verify.py 检查
3. 用户手动验证输出
4. 更新此清单
