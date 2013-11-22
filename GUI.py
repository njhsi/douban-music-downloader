#!/usr/bin/env python
#encoding:utf-8

from Tkinter import *
from ImageTk import PhotoImage
import os
import threading
import webbrowser

class ToolGUI():
    def __init__(self):
        self.root = root = Tk()
        root.withdraw()
        root.title(u'吉敏豆瓣音乐下载工具 4.0')
        self.screen_width = screen_width = root.winfo_screenwidth()
        self.screen_height = screen_height = root.winfo_screenheight() - 100
        root.resizable(False,False)

        self.icon = icon = PhotoImage(file='icon.gif')
        root.tk.call('wm', 'iconphoto', root._w, icon)
        Label(root, text=u'请悉知', foreground='brown'
              ).grid(row=0, sticky=E, padx=5, pady=10)
        Label(root, text=u'这是一个收费工具，试用时您可以下载\n红心兆赫前50首, 专辑前3首, 小站前10首.',
              foreground='brown', justify=LEFT).grid(row=0, column=1, sticky=W, pady=10)
        Label(root, text=u'程序需要访问您的红心歌曲,请登录豆瓣 ...'
              ).grid(row=1, column=1, sticky=W, pady=0)
        
        Label(root, text=u'用户名').grid(row=2, column=0, sticky=NW, padx=10, pady=10)
        self.txtUser = Entry(width=30)
        self.txtUser.grid(row=2, column=1, sticky=W, pady=10)
        self.txtUser.focus_set()
        Label(root, text=u'密 码').grid(row=3, column=0, sticky=NW, padx=10, pady=5)
        self.txtPass = Entry(width=30, show='*')
        self.txtPass.grid(row=3, column=1, sticky=W, pady=10)
        
        Label(root, text=u'验证码').grid(row=4, column=0, sticky=NW, padx=10, pady=5)
        self.txtCAPTCHA = Entry(width=30)
        self.txtCAPTCHA.grid(row=4, column=1, sticky=W, pady=5)
        self.txtCAPTCHA.bind('<Return>', self.cmd_login)
        
        self.lbl_CAPTCHA = Label(text=u'正在加载 ...', width=20, height=4, justify=LEFT)
        self.lbl_CAPTCHA.grid(row=5, column=1, sticky=NW, pady=5)

        self.cmdLogin = Button(root, text=u'登 录', state=DISABLED, width=5,
                               command=self.create_login_thread)
        self.cmdLogin.grid(row=6, column=1, sticky=W, pady=5)
        self.cmdLogin.bind('<Return>', self.cmd_login)
        
        self.cmdBuy = Button(root, text=u'购 买',
                             width=5, justify=RIGHT, command=lambda: self.cmd_buy(self))
        self.cmdBuy.grid(row=6, column=1, sticky=E, padx=30, pady=10)

        root.update_idletasks()
        root.deiconify()
        root.withdraw()
        root.geometry('%sx%s+%s+%s' % (root.winfo_width() + 10, root.winfo_height(),
                                       (screen_width - root.winfo_width())/2,
                                       (screen_height - root.winfo_height())/2) )
        root.deiconify()
        root.wm_protocol('WM_DELETE_WINDOW', self.on_quit)
        self.DEAD = False

    def mainWindow(self):
        self.mainform = mainform = Toplevel(self.root)
        mainform.tk.call('wm', 'iconphoto', mainform._w, self.icon)
        mainform.resizable(False,False)
        
        Label(mainform, text=u'文件保存路径:',
              foreground='brown', justify=LEFT).grid(row=0, column=0, padx=10, pady=10, sticky=W)
        self.path_var = StringVar()
        self.path_var.set(os.getcwd())
        self.txtPath = Entry(mainform, width=50, textvariable=self.path_var)
        self.txtPath.grid(row=0, column=1, pady=10, sticky=EW)

        info = u'%s, 您已加红心 %s 首' % (self.douban_user, self.douban_liked_count)
        if self.vip_1 or self.vip_2:
            info += u' 感谢您购买本程序.'
        else:
            info += u' 当前为免费试用版.'
        Label(mainform, text=info,
              foreground='brown').grid(row=1, columnspan=2, padx=10, pady=5, sticky=W)

        self.cmdDown = Button(mainform, text=u'下载红心音乐',
                              command=lambda: self.cmd_down_liked(self))
        self.cmdDown.grid(row=2, column=0, sticky=EW, padx=10, pady=10)

        self.cmdDownAlbum = Button(mainform, text=u'下载专辑',
                                   command=self.create_down_album_thread)
        self.cmdDownAlbum.grid(row=3, column=0, sticky=EW, padx=10, pady=10)
        self.douban_album_url = StringVar()
        self.douban_album_url.set('http://music.douban.com/subject/1415369/')
        self.txtAlbum = Entry(mainform, textvariable=self.douban_album_url)
        self.txtAlbum.grid(row=3, column=1, sticky=EW, pady=10)

        self.cmdDownSite = Button(mainform, text=u'下载小站音乐',
                                   command=self.create_down_site_thread)
        self.cmdDownSite.grid(row=4, column=0, sticky=EW, padx=10, pady=10)
        self.douban_site_url = StringVar()
        self.douban_site_url.set('http://site.douban.com/dingke/')
        self.txtSite = Entry(mainform, textvariable=self.douban_site_url)
        self.txtSite.grid(row=4, column=1, sticky=EW, pady=10)

        self.lbl_status = Label(mainform, text='...',
                                height=4, justify=LEFT, foreground='purple', wraplength=400)
        self.lbl_status.grid(row=6, column=1, columnspan=1, sticky=W, padx=0)
        
        mainform.update_idletasks()
        mainform.deiconify()
        mainform.withdraw()
        mainform.geometry('%sx%s+%s+%s' %
                          (mainform.winfo_width() + 10, mainform.winfo_height(),
                           (self.screen_width - mainform.winfo_width())/2,
                           (self.screen_height - mainform.winfo_height())/2) )
        mainform.deiconify()
        mainform.wm_protocol('WM_DELETE_WINDOW', self.on_quit)
        self.cmdDown.focus_set()
        mainform.mainloop()        

    def on_quit(self):
        self.DEAD = True    # App dead, all other threads should exit
        try:
            self.root.destroy()
            self.mainform.destroy()
        except:
            pass
        
    def cmd_login(self, event):
        pass
    def cmd_buy(self, event):
        browser = webbrowser.get()
        browser.open('http://xigongda.org/douban/')
    def cmd_down_liked(self, event):
        pass
    def cmd_down_album(self, event):
        pass
    def cmd_down_site(self, event):
        pass
    def create_login_thread(self):
        threading.Thread(target=self.cmd_login, args=(self,)).start()
    def create_down_album_thread(self):
        threading.Thread(target=self.cmd_down_album, args=(self,)).start()
    def create_down_site_thread(self):
        threading.Thread(target=self.cmd_down_site, args=(self,)).start()