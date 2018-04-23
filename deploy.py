#!/usr/bin/python2
# -*- coding:utf-8 -*-
import glob
import os
import shutil
import sys
import ConfigParser
from os.path import join

BASE_PATH = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))

config = {
    'project': {
        'url': '',
        'name': ''
    },
    'tomcat': {
        'bin': '',
        'webapps': ''
    },
    'package': {
        'out_dir': 'target',
        'name': '',
    }
}


def get_config():
    """获取配置，不同的项目可以通过修改配置文件实现"""
    print('读取构建配置:')
    global config
    cfg = ConfigParser.ConfigParser()
    cfg.read('config.ini')
    try:
        config['project']['url'] = cfg.get('project', 'url')
        config['project']['name'] = cfg.get('project', 'name')

        config['tomcat']['bin'] = cfg.get('tomcat', 'bin')
        config['tomcat']['webapps'] = cfg.get('tomcat', 'webapps')

        config['package']['out_dir'] = cfg.get('package', 'out_dir')
        config['package']['name'] = cfg.get('package', 'name')

    except ConfigParser.NoSectionError as e:
        raise ValueError('section： %s 不能为空' % e.section)
    except ConfigParser.NoOptionError as e:
        raise ValueError('section-option： %s - %s 不能为空' % (e.section, e.option))
    print(config)


def chdir(path):
    print('定位目录: %s' % path)
    os.chdir(path)


def get_project_path():
    return join(BASE_PATH, config['project']['name'])


def svn_up():
    # 撤销本地修改避免冲突，更新到最新版本
    print('部署: 下载更新代码')
    os.system('svn checkout %s' % config['project']['url'])
    chdir(get_project_path())
    rv = os.system('svn revert -R ./ && svn up ./')
    return rv


def package():
    print('部署: maven 打包')
    chdir(get_project_path())
    rv = os.system('mvn clean package')
    assert rv == 0, 'maven 打包构建失败!'
    war_path = join(get_project_path(), config['package']['out_dir'], config['package']['name'])
    file_list = glob.glob(war_path + '*.war')
    assert len(file_list) == 1, '获取war异常， %s' % file_list
    print('输出war : %s ' % file_list[0])
    return file_list[0]


def deploy(war_path):
    print('部署: 复制war到webapps start')
    webapps_path = config['tomcat']['webapps']
    assert os.path.isdir(webapps_path) and os.path.exists(webapps_path), 'webapps 路径异常, %s' % webapps_path
    webapp_war = join(webapps_path, config['package']['name']) + '.war'
    tomcat_stop()
    if os.path.exists(webapp_war) and os.path.isfile(webapp_war):
        print('删除旧的war, %s' % webapp_war)
        os.remove(webapp_war)

    old_webapp = join(webapps_path, config['package']['name'])
    if os.path.exists(old_webapp) and os.path.isdir(old_webapp):
        print('删除旧的webapp, %s' % old_webapp)
        shutil.rmtree(old_webapp)

    print('部署: 复制%s 到 %s ' % (war_path, webapp_war))
    shutil.copyfile(war_path, webapp_war)
    # 解压， 如果让tomcat自己解压的话，会被部署到ROOT去
    os.system('unzip %s -d %s > /dev/null 2>&1' % (webapp_war, old_webapp))
    tomcat_start()


def tomcat_stop():
    chdir(config['tomcat']['bin'])
    print('部署: 停止tomcat')
    os.system('./shutdown.sh')
    pass


def tomcat_start():
    chdir(config['tomcat']['bin'])
    print('部署: 重启tomcat')
    os.system('./startup.sh')


def only_copy_static():
    """如果是只更新jsp文件的话，无需重新打包和重启tomcat"""
    print("更新jsp和资源文件: start")
    get_config()
    svn_up()
    src_webapp_dir = join(BASE_PATH, config['project']['name'], 'src/main/webapp')
    ignore_dir = join(BASE_PATH, config['project']['name'], 'src/main/webapp/WEB-INF')
    webapp_dir = join(config['tomcat']['webapps'], config['package']['name'])

    def remove(path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    files_or_dirs = glob.glob(src_webapp_dir + "/*")
    for file_or_dir in files_or_dirs:
        if os.path.abspath(file_or_dir) == ignore_dir:
            continue
        dst = join(webapp_dir, os.path.basename(file_or_dir))

        print("copy %s to %s" % (file_or_dir, dst))

        if os.path.exists(dst):
            remove(dst)

        if os.path.isfile(file_or_dir):
            shutil.copyfile(file_or_dir, dst)
        else:
            shutil.copytree(file_or_dir, dst)
    print("更新jsp和资源文件: end")


if __name__ == '__main__':
    print('部署: start')
    get_config()
    svn_up()
    war = package()
    deploy(war)
    print('部署: end')
