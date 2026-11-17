"""手游资源热更新核心工具。

覆盖六类线上事故对应的修复点：
- manifest 记录依赖与版本，diff 出 added/removed/changed，而不是只比对整体 hash；
- 断点续传的 range 请求严格解析并校验，CDN 回源返回整文件时客户端能识别；
- 下载块先校验 sha256，通过后才允许原子替换正式文件（校验由 verify_chunk 把关）；
- 回滚同时清理已下载的多余 bundle，而不是只回滚 manifest；
- 差分按内容块比对，只下载变化的块；
- manifest 按平台维度隔离（调用方按平台各持一份，diff 在单平台内进行）。
"""

import hashlib


def manifest_diff(old, new):
    """比对两份 manifest（资源名 -> 版本/指纹），返回新增、删除、变更列表。

    版本号或依赖指纹任一变化都算 changed，避免"依赖变了但版本没变"漏更。
    """
    old = old or {}
    new = new or {}
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    changed = sorted(k for k in old if k in new and old[k] != new[k])
    return {'added': added, 'removed': removed, 'changed': changed}


def parse_range(header, size):
    """解析 HTTP Range 头，返回闭区间 (start, end)。

    - 'bytes=0-99'  -> (0, 99)
    - 'bytes=-100'  -> 最后 100 字节
    - 'bytes=0-'    -> 从 0 到文件尾
    越界时 end 收敛到 size-1；格式非法、区间为空或起点越界抛 ValueError，
    让调用方识别"回源返回了整文件"这类异常而不是默默接受。
    """
    if not isinstance(header, str) or not header.startswith('bytes='):
        raise ValueError(f'invalid range header: {header!r}')
    if size is None or size <= 0:
        raise ValueError(f'invalid size: {size!r}')

    spec = header[len('bytes='):].strip()
    if ',' in spec:  # 不支持多段 range
        raise ValueError(f'multiple ranges not supported: {header!r}')
    parts = spec.split('-', 1)
    if len(parts) != 2:
        raise ValueError(f'invalid range spec: {spec!r}')
    start_s, end_s = parts[0].strip(), parts[1].strip()

    if start_s == '':
        # 后缀形式：bytes=-N 表示最后 N 字节
        if not end_s.isdigit():
            raise ValueError(f'invalid suffix range: {spec!r}')
        n = int(end_s)
        if n <= 0:
            raise ValueError(f'empty suffix range: {spec!r}')
        start = max(size - n, 0)
        end = size - 1
    else:
        if not start_s.isdigit():
            raise ValueError(f'invalid range start: {spec!r}')
        start = int(start_s)
        if end_s == '':
            end = size - 1
        else:
            if not end_s.isdigit():
                raise ValueError(f'invalid range end: {spec!r}')
            end = min(int(end_s), size - 1)

    if start >= size or start > end:
        raise ValueError(f'unsatisfiable range: {spec!r} for size {size}')
    return (start, end)


def diff_blocks(old, new, block_size):
    """按内容块比对新旧数据，返回发生变化的块下标列表。

    只传输变化的块，避免"改 1KB 配置下载 50MB"。
    新旧长度不一致时，多出来的块也算变更。
    """
    if block_size <= 0:
        raise ValueError(f'invalid block_size: {block_size!r}')
    old = old or b''
    new = new or b''
    n_blocks = max((len(old) + block_size - 1) // block_size,
                   (len(new) + block_size - 1) // block_size)
    changed = []
    for i in range(n_blocks):
        lo, hi = i * block_size, (i + 1) * block_size
        if old[lo:hi] != new[lo:hi]:
            changed.append(i)
    return changed


def rollback_plan(downloaded, target):
    """回滚计划：返回需要从本地清理的 bundle 列表。

    downloaded 是本地已下载的 bundle 集合，target 是回滚目标 manifest
    需要的 bundle 集合；凡是目标里不需要的一律清理，保证版本回退后
    资源与 manifest 一致。
    """
    return sorted(set(downloaded) - set(target))


def verify_chunk(data, expected_sha256):
    """校验下载块的 sha256，通过后才允许原子替换正式文件。"""
    digest = hashlib.sha256(data).hexdigest()
    return digest == expected_sha256.lower()
