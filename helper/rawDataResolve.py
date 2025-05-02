
import traceback
import re
import json

from ioService import writer


# 粉專與社團文章抓取共用
def __resolverEdgesPage__(edge) -> dict:

    ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
    comet_sections_ = edge['node']['comet_sections']

    # name
    try:
        name = comet_sections_['context_layout']['story']['comet_sections']['actor_photo']['story']['actors'][0]['name']

        story_id = edge['node']['id']
        try:
            # creation_time
            creation_time = comet_sections_['context_layout']['story']['comet_sections']['metadata'][0]['story']['creation_time']
            # url
            url = comet_sections_['context_layout']['story']['comet_sections']['metadata'][0]['story']['url']
        except:
            # creation_time
            creation_time = comet_sections_['context_layout']['story']['comet_sections']['metadata'][1]['story']['creation_time']
            # url
            url = comet_sections_['context_layout']['story']['comet_sections']['metadata'][1]['story']['url']
       
        # message
        try:
            message = comet_sections_['content']['story']['message']['text']
        except:
            try:
                message = comet_sections_['content']['story']['comet_sections'].get('message', '').get('story', '').get(
                    'message', '').get('text', '') if comet_sections_['content']['story']['comet_sections'].get('message', '') else ''
            except:
                try:
                    message = comet_sections_['content']['story']['comet_sections']['message']['rich_message'][0]['text']
                except:
                    message = ""
        
        # 針對分享主體本身沒有內容的狀況下，嘗試拿被分享的內容來做為內容填充
        if message == "":
            try:
                message = comet_sections_['content']['story']['attached_story']['message']['text']
            except:
                message = ""

        message = ILLEGAL_CHARACTERS_RE.sub(r'', message)
        # postid
        postid = edge['node']['post_id']
        # actorid
        pageid = comet_sections_['context_layout']['story']['comet_sections']['actor_photo']['story']['actors'][0]['id']
        
        if "comet_feed_ufi_container" in comet_sections_['feedback']['story']:
            feedback_root = comet_sections_['feedback']['story']['comet_feed_ufi_container']
            feedback_main_node = feedback_root["story"]["story_ufi_container"]["story"]["feedback_context"]["feedback_target_with_context"]
            # comment_count 留言
            comment_count = feedback_main_node["comment_rendering_instance"]["comments"]["total_count"]
            # reaction_count 按讚
            reaction_count = feedback_main_node["comet_ufi_summary_and_actions_renderer"]["feedback"]["reaction_count"]["count"]
            # share_count 分享
            share_count = feedback_main_node["comet_ufi_summary_and_actions_renderer"]["feedback"]["share_count"]["count"]
            # feedback_id
            feedback_id = feedback_root['story']['feedback_context']['feedback_target_with_context']['id']
        elif "story_ufi_container" in comet_sections_['feedback']['story']:
            feedback_root = comet_sections_['feedback']['story']['story_ufi_container']
            feedback_main_node = feedback_root["story"]["feedback_context"]["feedback_target_with_context"]["comet_ufi_summary_and_actions_renderer"]["feedback"]
            # comment_count 留言
            try:
                comment_count = feedback_main_node["comment_rendering_instance"]["comments"]["total_count"]
            except:
                print("沒有抓到正確留言數")
                comment_count = 0
            # reaction_count 按讚
            reaction_count = feedback_main_node["reaction_count"]["count"]
            # share_count 分享
            share_count = feedback_main_node["share_count"]["count"]
            # feedback_id
            feedback_id = comet_sections_["feedback"]["story"]["feedback_context"]["feedback_target_with_context"]["id"]
        else :
            feedback_root = comet_sections_['feedback']['story']['feedback_context']
            feedback_main_node = feedback_root["feedback_target_with_context"]["ufi_renderer"]["feedback"]["comet_ufi_summary_and_actions_renderer"]["feedback"]
            # comment_count 留言
            try:
                comment_count = feedback_main_node["total_comment_count"]
            except:
                print("沒有抓到正確留言數")
                comment_count = 0
            # reaction_count 按讚
            reaction_count = feedback_main_node["reaction_count"]["count"]
            # share_count 分享
            share_count = feedback_main_node["share_count"]["count"]
            # feedback_id
            feedback_id = feedback_root["feedback_target_with_context"]["id"]
        # poster_name
        poster_name = comet_sections_['content']['story']['actors'][0]['name']

        # poster_url
        poster_url = comet_sections_['content']['story']['actors'][0]['url']
        if poster_url == "":
            poster_url = f"https://www.facebook.com/profile.php?id={comet_sections_['content']['story']['actors'][0]['id']}"
    # cursor
    except:
        writer.writeLogToFile(f"*規格不符的文章資料* 錯誤細節待查：{edge}", True)
        name = ""
        story_id = ""
        creation_time = 0
        message = ""
        postid = ""
        pageid = ""
        comment_count = ""
        reaction_count = ""
        share_count = ""
        feedback_id = ""
        url = ""
        poster_name = ""
        poster_url = ""

    image_url = ""
    video_url = ""
    try:
        attachments_type = comet_sections_["content"]["story"]["attachments"][0]["target"]["__typename"]

        if attachments_type == "Video":
            video_url = comet_sections_["content"]["story"]["attachments"][0]["styles"]["attachment"]["url"]
        elif attachments_type == "Photo":
            attach_obj = comet_sections_['content']['story']['attachments'][0]['styles']['attachment']
            # 單張圖片
            if "media" in attach_obj:
                if "photo_image" in attach_obj['media']:
                    image_url = attach_obj['media']['photo_image']['uri']
                elif "image" in attach_obj['media']:
                    image_url = attach_obj['media']['image']['uri']
                elif "placeholder_image" in attach_obj['media']:
                    image_url = attach_obj['media']['placeholder_image']['uri']
                else:
                    image_url = ""
            # 多張圖片
            elif "all_subattachments" in attach_obj:
                try:
                    image_url = attach_obj['all_subattachments']['nodes'][0]['media']['image']['uri']
                except:
                    pass
                finally:
                    image_url = ""
            else:
                image_url = ""
    except:
        print(f"這篇文章不含多媒體資源: {url}")

    cursor = edge['cursor']

    dict_output = {
        "name": name,
        "story_id": story_id,
        "creation_time": creation_time,
        "message": message,
        "post_id": postid,
        "page_id": pageid,
        "feedback_id": feedback_id,
        "comment_count": comment_count,
        "reaction_count": reaction_count,
        "share_count": share_count,
        "url": url,
        "image_url": image_url,
        "video_url": video_url,
        "cursor": cursor,
        "poster_name": poster_name,
        "poster_url": poster_url
    }

    return dict_output
    # return [name, creation_time, message, postid, pageid,feedback_id, comment_count, reaction_count, share_count,url,image_url, cursor]


def __resolverEdgesFeedback__(edge, posts_count) -> dict:
    comet_sections_ = edge['node']['comet_sections']
    ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')

    # 特殊的tracking data, 主要是為了抓正確格式的sharer id, 一般欄位的id似乎是加密過的,不好閱讀ex : pfbid02c61dhddXYmAexrJck1GREeLrxuBVZmkkLM7vTBwCbmxqEfmcntm68c77Nrbhn8WJl
    tracking_data_str = comet_sections_['feedback']['story']['tracking']
    tracking_data = json.loads(tracking_data_str)

    # 分享者名稱
    sharer_name = comet_sections_[
        'context_layout']['story']['comet_sections']['title']['story']['actors'][0]['name']

    # 分享時間
    try:
        create_time = comet_sections_[
            'context_layout']['story']['comet_sections']['metadata'][0]['story']['creation_time']
    except:
        try:
            create_time = comet_sections_['context_layout']['story']['comet_sections']['metadata'][1]['story']['creation_time']
        except:
            create_time = comet_sections_['context_layout']['story']['comet_sections']['metadata'][2]['story']['creation_time']

    # 分享者id
    sharer_id = tracking_data['content_owner_id_new']
    # 內容
    contents_check_point = comet_sections_['content']['story']['comet_sections']['message']
    if contents_check_point is None:
        contents = ""
    else:
        try:
            contents = contents_check_point['story']['message']['text']
        except:
            try:
                contents = contents_check_point['story']['rich_message'][0]['text']
            except:
                contents = ""

    contents = ILLEGAL_CHARACTERS_RE.sub(r'', contents)

    # 被分享者可能不存在
    # 被分享者名稱(需另外處理)
    # 若是從某人分享到某個單人而非社團的話，只會有名字，不會有ＩＤ
    been_sharer_check_point = comet_sections_[
        'context_layout']['story']['comet_sections']['title']['story']
    if 'to' in been_sharer_check_point:
        been_sharer_raw_name = been_sharer_check_point['to']['name']
        # 被分享者網址
        if edge['node']['feedback']['associated_group'] is not None:
            been_sharer_id = edge['node']['feedback']['associated_group']['id']
        else:
            been_sharer_id = ""
    else:
        been_sharer_raw_name = ""
        been_sharer_id = ""

    # 分享行為產生的單頁連結
    permalink = comet_sections_['feedback']['story']['url']
    if permalink is None:
        permalink = ""

    # cursor
    cursor = edge['cursor']

    dict_output = {
        "posts_count": str(posts_count),
        "sharer_name": sharer_name,
        "create_time": create_time,
        "sharer_id": sharer_id,
        "contents": contents,
        "been_sharer_raw_name": been_sharer_raw_name,
        "been_sharer_id": been_sharer_id,
        "permalink": permalink,
        "cursor": cursor
    }

    return dict_output
    # return [str(posts_count),sharer_name,create_time,sharer_id,contents,been_sharer_raw_name,been_sharer_id,cursor]


def __resolverEdgesSectionAbout__(edge, aboutNumber) -> dict:
    # 0:總覽，1:學歷與工作經歷，2:住過的地方，3:聯絡和基本資料，4:家人和感情狀況
    match aboutNumber:
        case 0:
            about_id_list = []
            name = "總覽"
            for obj in edge['all_collections']['nodes']:
                id = obj['id']
                about_id_list.append(id)
            dict_output = {
                "id_output": about_id_list,
                "name": name
            }
            return dict_output
        case 1:
            start_point = edge['activeCollections']['nodes'][0]['style_renderer']['profile_field_sections']
            name = "學經歷"
            work_name_list = []
            work_link_list = []
            work_date_list = []
            college_name_list = []
            college_link_list = []
            college_date_list = []
            highSchool_name_list = []
            highSchool_link_list = []
            highSchool_date_list = []

            for number in range(0, len(start_point)):
                profile_fields = start_point[number]["profile_fields"]["nodes"]
                for inner_number in range(0, len(profile_fields)):
                    if profile_fields[inner_number]['field_type'] == "null_state":
                        break
                    else:
                        match number:
                            case 0:  # 工作
                                work_name_list.append(
                                    profile_fields[inner_number]['title']['text'])
                                if len(profile_fields[inner_number]['list_item_groups']) != 0:
                                    work_date_list.append(
                                        profile_fields[inner_number]['list_item_groups'][0]['list_items'][0]['text']['text'])
                                else:
                                    work_date_list.append("")
                                if len(profile_fields[inner_number]['title']['ranges']) != 0:
                                    if profile_fields[inner_number]['title']['ranges'][0]['entity'] is None:
                                        work_link_list.append("")
                                    else:
                                        work_link_list.append(
                                            profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                                else:
                                    work_link_list.append("")
                            case 1:  # 大專院校
                                college_name_list.append(
                                    profile_fields[inner_number]['title']['text'])
                                if len(profile_fields[inner_number]['list_item_groups']) != 0:
                                    college_date_list.append(
                                        profile_fields[inner_number]['list_item_groups'][0]['list_items'][0]['text']['text'])
                                else:
                                    college_date_list.append("")
                                if len(profile_fields[inner_number]['title']['ranges']) != 0:
                                    if profile_fields[inner_number]['title']['ranges'][0]['entity'] is None:
                                        college_link_list.append("")
                                    else:
                                        college_link_list.append(
                                            profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                                else:
                                    college_link_list.append("")
                            case 2:  # 高中
                                highSchool_name_list.append(
                                    profile_fields[inner_number]['title']['text'])
                                if len(profile_fields[inner_number]['list_item_groups']) != 0:
                                    highSchool_date_list.append(
                                        profile_fields[inner_number]['list_item_groups'][0]['list_items'][0]['text']['text'])
                                else:
                                    highSchool_date_list.append("")
                                if len(profile_fields[inner_number]['title']['ranges']) != 0:
                                    if profile_fields[inner_number]['title']['ranges'][0]['entity'] is None:
                                        highSchool_link_list.append("")
                                    else:
                                        highSchool_link_list.append(
                                            profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                                else:
                                    highSchool_link_list.append("")

            about_work_dict = {
                "name": work_name_list,
                "link": work_link_list,
                "date": work_date_list
            }
            about_college_dict = {
                "name": college_name_list,
                "link": college_link_list,
                "date": college_date_list
            }
            about_highSchool_dict = {
                "name": highSchool_name_list,
                "link": highSchool_link_list,
                "date": highSchool_date_list
            }
            dict_output = {
                "name": name,
                "work": about_work_dict,
                "college": about_college_dict,
                "highSchool": about_highSchool_dict
            }
            return dict_output
        case 2:
            start_point = edge['activeCollections']['nodes'][0]['style_renderer']['profile_field_sections']
            name = "居住"
            live_name_list = []
            live_type_list = []
            live_link_list = []
            for number in range(0, len(start_point)):
                profile_fields = start_point[number]["profile_fields"]["nodes"]
                for inner_number in range(0, len(profile_fields)):
                    if profile_fields[inner_number]['field_type'] == "null_state":
                        break
                    else:
                        live_name_list.append(
                            profile_fields[inner_number]['title']['text'])
                        # current_city、hometown
                        live_type_list.append(
                            profile_fields[inner_number]['field_type'])
                        if len(profile_fields[inner_number]['title']['ranges']) != 0:
                            live_link_list.append(
                                profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                        else:
                            live_link_list.append("")

            about_live_dict = {
                "name": live_name_list,
                "link": live_link_list,
                "type": live_type_list
            }

            dict_output = {
                "name": name,
                "live": about_live_dict
            }
            return dict_output
        case 3:
            start_point = edge['activeCollections']['nodes'][0]['style_renderer']['profile_field_sections']
            name = "社群"
            phone = ""
            email = ""
            address = ""
            gender = ""
            birthday_date = ""
            birthday_year = ""
            social_name_list = []
            social_link_list = []
            social_type_list = []

            for number in range(0, len(start_point)):
                profile_fields = start_point[number]["profile_fields"]["nodes"]
                for inner_number in range(0, len(profile_fields)):
                    if profile_fields[inner_number]['field_type'] == "null_state":
                        break
                    else:
                        match number:
                            case 0:  # 聯絡
                                match profile_fields[inner_number]['field_type']:
                                    case "other_phone":
                                        phone = profile_fields[inner_number]['title']['text']
                                    case "address":
                                        address = profile_fields[inner_number]['title']['text']
                                    case "email":
                                        email = profile_fields[inner_number]['title']['text']
                                    case _:
                                        pass
                                        # print(f"{profile_fields[inner_number]['field_type']} 不是欲收集的聯絡資料")
                            case 1:  # 社群
                                social_name_list.append(
                                    profile_fields[inner_number]['title']['text'])
                                social_type_list.append(
                                    profile_fields[inner_number]['list_item_groups'][0]['list_items'][0]['text']['text'])
                                if profile_fields[inner_number]['link_url'] is None:
                                    social_link_list.append(
                                        profile_fields[inner_number]['title']['text'])
                                else:
                                    social_link_list.append(
                                        profile_fields[inner_number]['link_url'])
                            case 2:  # 基本資料
                                match profile_fields[inner_number]['field_type']:
                                    case "gender":
                                        gender = profile_fields[inner_number]['title']['text']
                                    case "birthday":
                                        if profile_fields[inner_number]['list_item_groups'][0]['list_items'][0]['text']['text'] == "Birth date":
                                            birthday_date = profile_fields[inner_number]['title']['text']
                                        else:
                                            birthday_year = profile_fields[inner_number]['title']['text']
                                    case _:
                                        pass
                                        # print(f"{profile_fields[inner_number]['field_type']} 不是欲收集的聯絡資料")
            about_social_dict = {
                "name": social_name_list,
                "link": social_link_list,
                "type": social_type_list
            }
            dict_output = {
                "name": name,
                "phone": phone,
                "email": email,
                "gender": gender,
                "address": address,
                "birthday_date": birthday_date,
                "birthday_year": birthday_year,
                "social": about_social_dict
            }

            return dict_output
        case 4:
            start_point = edge['activeCollections']['nodes'][0]['style_renderer']['profile_field_sections']
            name = "人際"
            relationship_name_list = []
            relationship_link_list = []
            relationship_type_list = []

            for number in range(0, len(start_point)):
                profile_fields = start_point[number]["profile_fields"]["nodes"]
                for inner_number in range(0, len(profile_fields)):
                    if profile_fields[inner_number]['field_type'] == "null_state":
                        break
                    else:
                        match number:
                            case 0:  # 感情狀況
                                # 單身
                                if len(profile_fields[inner_number]['list_item_groups']) != 0:
                                    relationship_name_list.append(
                                        profile_fields[inner_number]['title']['text'])
                                    relationship_type_list.append("情侶")
                                    if len(profile_fields[inner_number]['title']['ranges']) != 0:
                                        relationship_link_list.append(
                                            profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                                    else:
                                        relationship_link_list.append("")
                            case 1:  # 家人與親屬
                                relationship_name_list.append(
                                    profile_fields[inner_number]['title']['text'])

                                if len(profile_fields[inner_number]['list_item_groups']) != 0:
                                    relationship_type_list.append(profile_fields[inner_number]
                                                                  ['list_item_groups'][0]['list_items'][0]['text']['text'])
                                else:
                                    relationship_type_list.append("")

                                if len(profile_fields[inner_number]['title']['ranges']) != 0:
                                    relationship_link_list.append(
                                        profile_fields[inner_number]['title']['ranges'][0]['entity']['url'])
                                    if relationship_link_list[-1] is None:
                                        relationship_link_list[-1] = ""
                                else:
                                    relationship_link_list.append("")
            about_relationship_dict = {
                "name": relationship_name_list,
                "link": relationship_link_list,
                "type": relationship_type_list
            }

            dict_output = {
                "name": name,
                "relationship": about_relationship_dict
            }

            return dict_output
        case _:
            print(f"編號{str(aboutNumber)}為當前不需要的資料")
            return {}


def __resolverEdgesFriendzone__(edge) -> dict:
    name = edge['node']['title']['text']
    profile_url = edge['node']['url']
    cursor = edge['cursor']
    user_id = edge['node']['node']['id']

    if profile_url is None:
        profile_url = "https://www.facebook.com/profile.php?id=" + user_id

    dict_output = {
        "name": name,
        "url": profile_url,
        "userID": user_id,
        "cursor": cursor
    }

    return dict_output


def __resolverEdgesGroupMember__(edge) -> dict:
    name = edge['node']['name']
    profile_url = edge['node']['url']
    user_id = edge['node']['id']
    cursor = edge['cursor']

    if profile_url is None:
        profile_url = "https://www.facebook.com/profile.php?id=" + user_id

    dict_output = {
        "name": name,
        "url": profile_url,
        "userID": user_id,
        "cursor": cursor
    }

    return dict_output
