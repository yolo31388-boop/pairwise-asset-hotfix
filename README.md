# pairwise-asset-hotfix

手游每次热更新都提心吊胆：manifest 只比对文件 hash，资源依赖变了但版本号没变，客户端加载到旧 bundle；断点续传的 range 请求在 CDN 回源时返回整文件，进度条直接跳满；下载一半被杀进程，临时文件没有校验就替换正式文件，启动崩溃；回滚只回滚 manifest，不回滚已下载的 bundle，版本回退后资源对不上；差分包按固定块大小切，更新一个 1KB 配置却下了 50MB；多平台共用一份 manifest，Android 和 iOS 的纹理格式互相覆盖。game/asset_hotfix.py 是核心，tests/test_asset_hotfix.py 15个红。要修的是：manifest 记录依赖和版本；range 回源做校验；临时文件校验后原子替换；回滚同时清理 bundle；按内容差分；平台维度隔离 manifest。

## 运行

```bash
python -m pytest tests -q
```

初始状态：15 个用例失败。修复实现使全部用例通过，不要修改 `tests/` 下的测试。

语言/框架：Python 3, pytest；环境可复现等级：无外部依赖。
