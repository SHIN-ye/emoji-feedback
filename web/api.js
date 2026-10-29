// Model: session and API transport. Tokens live only in this tab's session storage.
export const auth={token:sessionStorage.getItem('token')||'',user:null};
export function save(token){auth.token=token;token?sessionStorage.setItem('token',token):sessionStorage.removeItem('token');}
export async function api(path,method='GET',body){
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(auth.token?{Authorization:'Bearer '+auth.token}:{})},...(body?{body:JSON.stringify(body)}:{})});
  const data=await response.json();
  if(!response.ok){if(response.status===401 && auth.user){save('');window.dispatchEvent(new Event('session-expired'));}throw new Error(data.message||'请求失败');}
  return data.data;
}
export async function exportCSV(query){
  const response=await fetch('/api/admin/emoji/export?'+query,{headers:{Authorization:'Bearer '+auth.token}});
  if(!response.ok)throw new Error((await response.json()).message||'导出失败');
  const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='课堂情绪记录.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
