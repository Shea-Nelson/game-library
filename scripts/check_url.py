import sys,json,subprocess,concurrent.futures as cf
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def chk(u):
    o=subprocess.run(["curl","-sL","-m","25","-A",UA,"-r","0-2047","-o","/dev/null","-w","%{http_code} %{content_type} %{url_effective}",u],capture_output=True,text=True).stdout
    p=o.split(" ",2); return u,{"code":p[0],"ctype":p[1] if len(p)>1 else "","final":p[2] if len(p)>2 else ""}
urls=[l.strip() for l in open(sys.argv[1]) if l.strip()]
with cf.ThreadPoolExecutor(6) as ex: res=dict(ex.map(chk,urls))
json.dump(res,open(sys.argv[2],"w"),indent=1)
for u,r in res.items(): print(r["code"],r["ctype"][:25],u)
