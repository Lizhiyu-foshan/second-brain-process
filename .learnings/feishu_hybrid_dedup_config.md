# Feishu 混合去重模式配置

## 功能开关

### FEISHU_HYBRID_DEDUP

启用混合去重模式（内存去重 + 文件去重）

**默认值**: `false`  
**推荐值**: `true`（生产环境）

**设置方式**:

1. **环境变量**（推荐）:
   ```bash
   export FEISHU_HYBRID_DEDUP=true
   ```

2. **在 Docker/Compose 中**:
   ```yaml
   environment:
     - FEISHU_HYBRID_DEDUP=true
   ```

3. **在 systemd 服务中**:
   ```ini
   [Service]
   Environment="FEISHU_HYBRID_DEDUP=true"
   ```

## 启用混合去重模式的效果

- **内存去重**：快速检查（O(1)），30 分钟 TTL
- **文件去重**：持久化兜底，12 小时窗口
- **降级机制**：如果 Python 调用失败，自动降级到仅内存去重

## 监控指标

启用后应该关注：

- 去重比例（预期：5-10% 的消息被识别为重复）
- 消息处理延迟（预期：增加 < 50ms）
- Python 调用失败率（预期：< 1%）

## 回滚

如果遇到问题，可以关闭混合去重模式：

```bash
export FEISHU_HYBRID_DEDUP=false
# 重启 OpenClaw 网关
openclaw gateway restart
```

---

**创建时间**: 2026-03-16  
**版本**: v1.0
