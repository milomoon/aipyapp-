class Plugin:
    """Trustoken all-in-one API plugin for AIPY
    """
    def on_exec(self, block):
        """
        执行代码事件
        param: block
        """
        block['content'] = block['content'].replace('https://restapi.amap.com/', 'https://api.trustoken.cn/aio-api/amap/')