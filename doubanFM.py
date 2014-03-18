#!/usr/bin/env python
#encoding:utf-8

from GUI import ToolGUI
from ImageTk import PhotoImage
from mutagen import File as FileKind
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
    def __init__(self):
        ToolGUI.__init__(self)
        self.busy_slaves = 0
        self.lock = threading.Lock()
    def slave_enter(self):    # Working
        self.lock.acquire()
        self.busy_slaves += 1
        self.lock.release()
    def slave_exit(self):    # Done
        self.lock.acquire()
        self.busy_slaves -= 1
        self.lock.release()
        
    def downCAPTCHA(self):
        self.cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        self.opener.addheaders = [('User-Agent',
                                   'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 \
                                   (KHTML, like Gecko) Chrome/31.0.1650.48 Safari/537.36')]
        urllib2.install_opener(self.opener)
        while True and not self.DEAD:
            try:
                self.CAPTCHA_id = CAPTCHA_id = urllib2.urlopen('http://douban.fm/j/new_captcha').read().strip('"')
                break
            except Exception, e:
                self.lbl_CAPTCHA.config(text=u'无法获取验证码...\n' + str(e))
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
            if os.path.exists(os.getcwd() + os.sep + u'user.dat'):
                key1 = md5.new(u''.join([self.douban_user, u'liked!@#']).encode('utf-8')).hexdigest()
                key2 = md5.new(u''.join([self.douban_url, u'liked!@#']).encode('utf-8')).hexdigest()
                key3 = md5.new(u''.join([self.douban_user, u'album!@#']).encode('utf-8')).hexdigest()
                key4 = md5.new(u''.join([self.douban_url, u'album!@#']).encode('utf-8')).hexdigest()
                key5 = md5.new(u''.join([self.douban_user, u'site!@#']).encode('utf-8')).hexdigest()
                key6 = md5.new(u''.join([self.douban_url, u'site!@#']).encode('utf-8')).hexdigest()
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
        for  script in scripts:
            self.douban_user_id_sign, res = ghost.evaluate(script+';window.SP;')
            #print script, 'xxxxxxxxx', self.douban_user_id_sign
            if self.douban_user_id_sign: break
        if not self.douban_user_id_sign: self.douban_user_id_sign='::'
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
            if song_add_count >= 500 and (not self.vip_1):
                break
            start += 15
        while not self.DEAD:
            if song_queue.empty() and self.busy_slaves == 0:
                self.cmdDown.config(state='normal')
                self.lbl_status.config(text=u'红心曲目全部下载完毕 :)')
                break
            else:
                time.sleep(0.2)

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
            if song_queue.empty() and self.busy_slaves == 0:
                self.cmdDownAlbum.config(state='normal')
                self.lbl_status.config(text=u'专辑曲目已下载完毕 :)')
                break
            else:
                time.sleep(0.2)


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
            if song_queue.empty() and self.busy_slaves == 0:
                self.cmdDownSite.config(state='normal')
                self.lbl_status.config(text=u'小站曲目已下载完毕 :)')
                break
            else:
                time.sleep(0.2)


    def down_slave(self):
        while True:
            item = song_queue.get()
            self.slave_enter()
            if item[0] == 'liked':
                type, song_path, song_id, song_title, song_artist = item
                save_path = os.path.join(app.douban_liked_folder,
                     self.valid_file_name(song_title + ' -' + song_artist) + '.mp3')
                self.douban_liked_down_count += 1
            elif item[0] == 'album':
                type, song_id, ssid, song_artist, song_title = item
                save_path = os.path.join(self.douban_album_folder,
                                         self.valid_file_name(song_title + ' -' + song_artist) + '.mp3')
            elif item[0] == 'site':
                type, song_title, song_url = item
                save_path = os.path.join(self.douban_site_folder,
                                         self.valid_file_name(song_title) + '.mp3')
            if os.path.exists(save_path) or os.path.exists(save_path[:-4]+'.m4a'):
                self.lbl_status.config(text=u'文件已经存在: 《%s》' % song_title)
                song_queue.task_done()
                self.slave_exit()
                continue    # Files exists

            try:
                if item[0] == 'liked':
                    for i in range(3):    # try 3 times at most
                        try:
                            html_doc = urllib2.urlopen(song_path).read().decode('utf-8')
                        except Exception as e:
                            if str(e).find('HTTP Error 403') > 0:
                                time.sleep(3)
                            else:
                                pass
                    ssid = re.search('<li class="song-item" id="%s" data-ssid="(\w+)">' % song_id, html_doc).group(1)
                if type != 'site': # Need fetch url first
                    json_doc = app.post('http://music.douban.com/j/songlist/get_song_url',
                                        {'sid': song_id, 'ssid': ssid, 'ck': app.douban_ck})
                    song_url = json.loads(json_doc)['r']
                    
                for i in range(3):
                    try:
                        mp3_data = urllib.urlopen(song_url).read()
                        with open(save_path, 'wb') as outFile:
                            outFile.write(mp3_data)
                        filekind = FileKind(save_path)
                        if [x for x in filekind.mime if ('mp4' in x or 'm4a' in x)]: os.rename(save_path, save_path[:-4]+'.m4a')
                        break
                    except Exception as e:
                        print 'song urlopen error:', e
            except Exception as e:
                print 'unexpected error:', e, song_path
                song_queue.task_done()
                self.slave_exit()
                continue
            if type == 'liked':
                
                self.lbl_status.config(text=u'已下载红心曲目 %s / %s:\n%s' %
                                      (self.douban_liked_down_count,
                                       self.douban_liked_count,
                                       song_title + ' - ' + song_artist))
            elif type == 'album':
                self.lbl_status.config(text=u'专辑曲目下载完成:\n%s' %
                                       song_title + ' - ' + song_artist)
            elif type == 'site':
                self.lbl_status.config(text=u'小站曲目下载完成:\n%s' %
                                       song_title)
            song_queue.task_done()
            self.slave_exit()
            time.sleep(0.01)


    def valid_file_name(self, file_name):    # Some invalid chars should be replaced
        rstr = r'[\/\\\:\*\?\"\<\>\|]'
        return re.sub(rstr, '', file_name).strip()
    

song_queue = Queue.Queue()    # In case APP blocked by douban, Only 10 items allowed, add on 2013-12-12
app = Downloader()
threading.Thread(target=app.downCAPTCHA).start()    # Down CAPTCHA

max_threads = 3
file_path = os.path.join(os.getcwd(), 'threads.txt')
if os.path.exists(file_path):
    with open('threads.txt') as inFile:
        try:
            max_threads = int(inFile.read())
        except:
            pass

for i in range(max_threads):
    slave_thread = threading.Thread(target=app.down_slave, args=())
    slave_thread.setDaemon(True)
    slave_thread.start()
app.root.mainloop()
