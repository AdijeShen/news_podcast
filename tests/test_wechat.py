# https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN
# POST 请求
# {
#     "articles": [
#         // 图文消息结构
#         {
#             "article_type":"news",
#             "title":TITLE,
#             "author":AUTHOR,
#             "digest":DIGEST,
#             "content":CONTENT,
#             "content_source_url":CONTENT_SOURCE_URL,
#             "thumb_media_id":THUMB_MEDIA_ID,
#             "need_open_comment":0,
#             "only_fans_can_comment":0,
#             "pic_crop_235_1":X1_Y1_X2_Y2,
#             "pic_crop_1_1":X1_Y1_X2_Y2
#         },
# }


def test_get_access_token():
    """测试获取access_token"""
    import requests
    from dotenv import load_dotenv
    import os

    load_dotenv()
    
    # 微信公众号的appid和secret
    appid = os.getenv("WECHAT_APPID")
    secret = os.getenv("WECHAT_SECRET")
    
    # 请求URL
    url = f"https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": appid,
        "secret": secret
    }
    
    # 发送请求
    response = requests.get(url, params=params)
    
    # 打印响应结果,方便调试
    print(response.json())
    
    # 检查响应
    assert response.status_code == 200
    result = response.json()
    assert "access_token" in result
    assert "expires_in" in result
    assert result["expires_in"] == 7200  # token有效期应为7200秒



def test_batchget_material():
    """测试批量获取永久素材"""
    import requests
    
    access_token = "91_rDNA2SBWAv9CSLNmG9ZVYIC4Dg_obdCbJYXNv15OmW24dWFgmTM0Dl-SEXVQfE9J2Vzc_Vs3rAJ_G3Y_WkL4IS-41uKu8SAMs-JNYA0mBut5Lm3xwfOW4Ocx-rIGPVbADAMVB"
    
    # 请求URL
    url = f'https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}'
    
    # 请求参数
    data = {
        "type": "image", # 素材类型,可以是image,video,voice,news
        "offset": 0,     # 从全部素材的该偏移位置开始返回
        "count": 20      # 返回素材的数量,取值在1到20之间
    }
    
    # 发送请求
    response = requests.post(url, json=data)

    print(response.json())
    
    # 检查响应
    assert response.status_code == 200
    result = response.json()
    assert 'item_count' in result
    assert 'item' in result


media_id='5gnVOxWARHoHvrXEq52JeAmJ9oN4VomYalfSBU7ZbnBMM3p32xQF7lXMG1Swej4V'


def test_add_draft():
    """测试添加草稿功能"""
    import requests
    from typing import Dict, Any
    import pytest
    from datetime import datetime
    import json
    
    # 使用现有的access_token或从环境变量获取
    # 这里使用固定值，实际使用时应该调用获取token的函数
    access_token = "91_rDNA2SBWAv9CSLNmG9ZVYIC4Dg_obdCbJYXNv15OmW24dWFgmTM0Dl-SEXVQfE9J2Vzc_Vs3rAJ_G3Y_WkL4IS-41uKu8SAMs-JNYA0mBut5Lm3xwfOW4Ocx-rIGPVbADAMVB"  # 替换为有效的access_token
    
    # 请求URL
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    
    # 当前时间作为标题的一部分，确保每次测试标题不同
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 请求参数
    data: Dict[str, Any] = {
        "articles": [
            {
                "article_type": "news",
                "title": f"测试标题 {current_time}",
                "author": "百晓生",
                "digest": "测试摘要内容",
                "content": "<p>这是一篇测试文章，用于测试草稿添加功能</p>",
                "thumb_media_id": media_id,  # 使用已上传的素材ID
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }
        ]
    }
    
    # 如果没有有效的access_token，跳过测试
    if access_token == "YOUR_ACCESS_TOKEN":
        pytest.skip("没有提供有效的access_token")
    
    # 将数据转换为JSON字符串，确保unicode编码正确
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # 发送请求时指定Content-Type和编码
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # 发送请求
    response = requests.post(url, data=json_data, headers=headers)
    
    # 打印响应结果，方便调试
    print(response.json())
    
    # 检查响应
    assert response.status_code == 200
    result = response.json()
    
    print(result)
    
    # 成功时，返回的JSON中应该有media_id字段
    if "errcode" not in result or result["errcode"] == 0:
        assert "media_id" in result
    else:
        # 如果出错但是错误码是45028（draft数量已达上限），也视为测试通过
        assert result["errcode"] in [0, 45028]