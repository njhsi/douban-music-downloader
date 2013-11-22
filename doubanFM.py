#!/usr/bin/env python
#encoding:utf-8

from GUI import ToolGUI
from ImageTk import PhotoImage
import threading
import urllib2, urllib
import cookielib
import json
import tkMessageBox
import re
from ghost import Ghost
import Queue
import time
import os
import md5


class Downloader(ToolGUI):
    def downCAPTCHA(self):
        self.cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        urllib2.install_opener(self.opener)
        while True:
            try:
                self.CAPTCHA_id = CAPTCHA_id = urllib2.urlopen('http://douban.fm/j/new_captcha').read().strip('"')
                break
            except:
                self.lbl_CAPTCHA.config(text=u'无法获取验证码, 重试...')
                time.sleep(1)
        with open('CAPTCHA.jpg', 'wb') as outFile:
            outFile.write(urllib2.urlopen('http://www.douban.com/misc/captcha?size=m&id=' + CAPTCHA_id).read())
        self.lbl_CAPTCHA.image = CAPTCHA_img = PhotoImage(file='CAPTCHA.jpg')
        self.lbl_CAPTCHA.config(text='', image=CAPTCHA_img, width=220, height=60)    # Pic width: 220px, height:60px
        self.root.after(10, self.lbl_CAPTCHA.update_idletasks)
        self.cmdLogin.config(state='normal')
        return

    def post(self, url, data):  
        req = urllib2.Request(url)  
        data = urllib.urlencode(data)
        response = self.opener.open(req, data)  
        return response.read()    # ResponseText not decoded yet

    def cmd_login(self, event):
        user = self.txtUser.get()
        passwd = self.txtPass.get()
        captcha = self.txtCAPTCHA.get()
        #user = ''    # Test user data
        #passwd = ''
        data = {'source': 'radio', 'alias': user, 'form_password': passwd,
                'captcha_id': self.CAPTCHA_id, 'captcha_solution': captcha
            }
        json_doc = self.post('http://douban.fm/j/login', data).decode('utf8')
        obj_json = json.loads(json_doc)
        if 'err_msg' in obj_json.keys():
            tkMessageBox.showinfo(u'登录失败',  u'*** %s ***' % obj_json['err_msg'])
            if obj_json['err_msg'] == u'验证码不正确':
                self.cmdLogin.config(state='disabled')
                self.downCAPTCHA()   # You know, this may take some time, but I'd rather let user wait
                self.txtCAPTCHA.delete(0, 'end')
                self.txtCAPTCHA.focus_set()
        else:
            user_info = obj_json['user_info']
            self.douban_url = user_info['url']
            self.douban_user = user_info['name']
            self.douban_liked_count = user_info['play_record']['liked']
            self.douban_ck = user_info['ck']
            # Check user level
            self.vip_1 = False
            self.vip_2 = False
            self.vip_3 = False
            if os.path.exists(os.getcwd() + os.sep + 'user.dat'):
                key1 = md5.new(self.douban_user + 'liked!@#').hexdigest()
                key2 = md5.new(self.douban_url + 'liked!@#').hexdigest()
                key3 = md5.new(self.douban_user + 'album!@#').hexdigest()
                key4 = md5.new(self.douban_url+ 'album!@#').hexdigest()
                key5 = md5.new(self.douban_user + 'site!@#').hexdigest()
                key6 = md5.new(self.douban_url+ 'site!@#').hexdigest()
                with open('user.dat', 'r') as inFile:
                    code_str = inFile.read()
                if code_str.find(key1) >= 0 or code_str.find(key2) >= 0:
                    self.vip_1 = True
                if code_str.find(key3) >=0 or code_str.find(key4) >= 0:
                    self.vip_2 = True
                if code_str.find(key5) >=0 or code_str.find(key6) >= 0:
                    self.vip_3 = True
            self.root.withdraw()    #hide login window, show mainWindow
            self.mainWindow()
        return

    def cmd_down_liked(self, event):
        self.cmdDown.config(state='disabled')
        self.lbl_status.config(text=u'正在获取曲目, 请稍后 ...')
        html_doc = urllib2.urlopen('http://douban.fm/mine#!type=liked&start=0').read().decode('utf-8')
        re_scripts = re.compile(r'<script>([\s\S]+?)</script>')
        scripts = re_scripts.findall(html_doc)
        script = scripts[-2]
        ghost = Ghost()
        self.douban_user_id_sign, res = ghost.evaluate(script+';window.user_id_sign;')
        for c in self.cookie:
            if c.name == 'bid':
                self.douban_bid = c.value.strip('"')
        self.douban_spbid = self.douban_user_id_sign + self.douban_bid
        threading.Thread(target=self.down_liked_master).start()
        return

    def down_liked_master(self):
        self.douban_liked_folder = os.path.join(self.path_var.get(),
                                                u'红心 - ' + self.valid_file_name(self.douban_user))
        if not os.path.exists(self.douban_liked_folder):
            os.mkdir(self.douban_liked_folder)
        start = 0    # Page 1
        song_add_count = 0
        self.douban_liked_down_count = 0
        while not self.DEAD:
            req = urllib2.Request('http://douban.fm/j/play_record?ck=%s&spbid=%s&type=liked&start=%s' %
                                  (self.douban_ck, self.douban_spbid, start))
            req.add_header('Referer', 'http://douban.fm/mine')
            response = self.opener.open(req)
            json_doc = response.read().decode('utf8', 'ignore')
            obj_json = json.loads(json_doc)
            if len(obj_json['songs']) == 0:
                break
            for song in obj_json['songs']:
                item = 'liked', song['path'], song['id'], song['title'], song['artist']
                song_queue.put(item)
                song_add_count += 1
            if song_add_count >= 50 and (not self.vip_1):
                break
            start += 15
            time.sleep(1)
        while not self.DEAD:
            if not song_queue.empty():
                time.sleep(0.2)
            else:
                self.cmdDown.config(state='normal')
                break

    def cmd_down_album(self, event):
        self.cmdDownAlbum.config(state='disabled')
        self.lbl_status.config(text=u'正在获取曲目, 请稍后 ...')
        html_doc = urllib2.urlopen(self.douban_album_url.get()).read().decode('utf-8')
        album_name = re.search('<h1>([\s\S]+?)</h1>', html_doc).group(1)
        self.douban_album_name = album_name = re.search('<span>(.*)</span>', album_name).group(1).strip()
        self.douban_album_folder = os.path.join(self.path_var.get(), self.valid_file_name(album_name))
        if not os.path.exists(self.douban_album_folder):
            os.mkdir(self.douban_album_folder)
        re_song_item = re.compile('<li class="song-item"[\s\S]+?</li>')
        re_song_id = re.compile('"song-item" id="(\d+?)"')
        re_ssid = re.compile('data-ssid="(\w+?)">')
        re_singer = re.compile('singer" value="(.+?)"/>')
        re_song_name = re.compile('data-title="(.+?)">')

        song_add_count = 0
        for song_li_tag in re_song_item.findall(html_doc):
            song_id = re_song_id.search(song_li_tag).group(1)
            ssid = re_ssid.search(song_li_tag).group(1)
            singer = re_singer.search(song_li_tag).group(1)
            song_title = re_song_name.search(song_li_tag).group(1)
            if song_add_count >= 3 and not self.vip_2:
                break
            item = 'album', song_id, ssid, singer, song_title
            song_queue.put(item)
            song_add_count += 1
        while not self.DEAD:
            if not song_queue.empty():
                time.sleep(0.2)
            else:
                self.cmdDownAlbum.config(state='normal')
                break

    def cmd_down_site(self, event):
        self.cmdDownSite.config(state='disabled')
        self.lbl_status.config(text=u'正在获取曲目, 请稍后 ...')
        html_doc = urllib2.urlopen(self.douban_site_url.get()).read().decode('utf-8')
        self.douban_site_name = re.search('<div class="sp-logo">[\s\S]+?alt="(.*?)"', html_doc).group(1).strip()
        self.douban_site_folder = os.path.join(self.path_var.get(),
                                               u'小站 - ' + self.valid_file_name(self.douban_site_name))
        if not os.path.exists(self.douban_site_folder):
            os.mkdir(self.douban_site_folder)
        re_song_records = re.compile('song_records = (\[[\s\S]+?\])')
        song_add_count = 0        
        for record in re_song_records.findall(html_doc):
            obj_json = json.loads(record)
            for song_item in obj_json: 
                song_title = song_item['name']
                song_url = song_item['rawUrl']
                item = 'site', song_title, song_url
                song_queue.put(item)
                song_add_count += 1
            if song_add_count >= 10 and not self.vip_3:
                break
        while not self.DEAD:
            if not song_queue.empty():
                time.sleep(0.2)
            else:
                self.cmdDownSite.config(state='normal')
                break

    def down_slave(self):
        while True:
            item = song_queue.get()                
            try:
                if item[0] == 'liked':
                    type, song_path, song_id, song_title, song_artist = item
                    html_doc = urllib2.urlopen(song_path).read().decode('utf-8')
                    ssid = re.search('<li class="song-item" id="%s" data-ssid="(\w+)">' % song_id, html_doc).group(1)
                elif item[0] == 'album':
                    type, song_id, ssid, song_artist, song_title = item
                elif item[0] == 'site':
                    type, song_title, song_url = item

                if type != 'site': # Need fetch url first
                    json_doc = app.post('http://music.douban.com/j/songlist/get_song_url',
                                        {'sid': song_id, 'ssid': ssid, 'ck': app.douban_ck})
                    song_url = json.loads(json_doc)['r']
                    
                if type == 'liked':
                    save_path = os.path.join(app.douban_liked_folder,
                                             self.valid_file_name(song_title + ' -' + song_artist) + '.mp3')
                elif type == 'album':
                    save_path = os.path.join(self.douban_album_folder,
                                             self.valid_file_name(song_title + ' -' + song_artist) + '.mp3')
                elif type == 'site':
                    save_path = os.path.join(self.douban_site_folder,
                                             self.valid_file_name(song_title) + '.mp3')
                for i in range(3):
                    if os.path.exists(save_path):
                        self.lbl_status.config(text=u'已存在的曲目: %s' % song_title)
                        break 
                    try:
                        mp3_data = urllib.urlopen(song_url).read()
                        with open(save_path, 'wb') as outFile:
                            outFile.write(mp3_data)
                        break
                    except Exception as e:
                        print e
                        pass
            except:
                pass
            if type == 'liked':
                self.douban_liked_down_count += 1
                self.lbl_status.config(text=u'已下载 %s / %s:\n%s' %
                                      (self.douban_liked_down_count,
                                       self.douban_liked_count,
                                       song_title + ' - ' + song_artist))
            elif type == 'album':
                self.lbl_status.config(text=u'下载完成专辑曲目:\n%s' %
                                       song_title + ' - ' + song_artist)
            elif type == 'site':
                self.lbl_status.config(text=u'下载完成小站曲目:\n%s' %
                                       song_title)
            song_queue.task_done()
            time.sleep(0.1)
            if song_queue.empty():
                if type == 'liked':
                    self.lbl_status.config(text=u'加心曲目已下载完成. ')
                elif type == 'album':
                    self.lbl_status.config(text=u'专辑《%s》已下载完成. ' % self.douban_album_name)
                elif type == 'site':
                    self.lbl_status.config(text=u'小站《%s》已下载完成. ' % self.douban_site_name)

    def valid_file_name(self, file_name):    # Some invalid chars should be replaced
        rstr = r'[\/\\\:\*\?\"\<\>\|]'
        return re.sub(rstr, '', file_name).strip()
    

song_queue = Queue.Queue()
app = Downloader()
threading.Thread(target=app.downCAPTCHA).start()    # Down CAPTCHA
for i in range(5):
    slave_thread = threading.Thread(target=app.down_slave, args=())
    slave_thread.setDaemon(True)
    slave_thread.start()
app.root.mainloop()