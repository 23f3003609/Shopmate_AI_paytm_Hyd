import os, re, json, base64, sqlite3, secrets, copy, time
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
app=FastAPI(title="ShopMate AI", version="1.0.0")

# In-memory bearer sessions: absolute five-minute lifetime, revoked on logout.
SESSION_TTL_SECONDS=300
SESSIONS={}
PUBLIC_API_PATHS={'/api/demo/login','/api/demo/register','/api/version','/api/health'}
@app.middleware("http")
async def token_auth_middleware(request: Request, call_next):
 path=request.url.path
 if path.startswith('/api/') and path not in PUBLIC_API_PATHS:
  auth=request.headers.get('authorization','')
  token=auth[7:].strip() if auth.lower().startswith('bearer ') else ''
  session=SESSIONS.get(token)
  if not session or session['expires_at']<=time.time():
   if token: SESSIONS.pop(token,None)
   return Response(content=json.dumps({'detail':'Session expired or invalid. Please log in again.'}),status_code=401,media_type='application/json')
  merchant_only=('/api/dashboard','/api/bill','/api/offers','/api/restock','/api/brief','/api/impact','/api/checklist','/api/demo/merchant','/api/demo/merchant/summary','/api/demo/events','/api/demo/customers','/api/demo/catalog','/api/demo/offers/send','/api/voice/')
  customer_only=('/api/demo/consent','/api/demo/customer/')
  customer_offers_only=(path=='/api/demo/offers')
  if any(path.startswith(prefix) for prefix in merchant_only) and session['role']!='merchant':
   return Response(content=json.dumps({'detail':'Merchant login required.'}),status_code=403,media_type='application/json')
  if (any(path.startswith(prefix) for prefix in customer_only) or customer_offers_only) and session['role']!='customer':
   return Response(content=json.dumps({'detail':'Customer login required.'}),status_code=403,media_type='application/json')
  request.state.session=session
 response=await call_next(request)
 response.headers['Cache-Control']='no-store'
 return response

# Munshi AI-style live Soundbox channel: payment events are pushed to merchant screens.
class MerchantSoundboxHub:
 def __init__(self): self.clients=set()
 async def connect(self, ws):
  await ws.accept(); self.clients.add(ws)
 def disconnect(self, ws): self.clients.discard(ws)
 async def broadcast(self, message):
  dead=[]
  for ws in list(self.clients):
   try: await ws.send_json(message)
   except Exception: dead.append(ws)
  for ws in dead: self.disconnect(ws)
soundbox_hub=MerchantSoundboxHub()

@app.websocket("/ws/merchant")
async def merchant_soundbox_ws(ws: WebSocket):
 token=ws.query_params.get('token',''); session=SESSIONS.get(token)
 if not session or session.get('role')!='merchant' or session['expires_at']<=time.time():
  await ws.close(code=4401); return
 await soundbox_hub.connect(ws)
 try:
  while True: await ws.receive_text()
 except WebSocketDisconnect:
  soundbox_hub.disconnect(ws)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
SARVAM_KEY=os.getenv("SARVAM_API_KEY","").strip()
CHAT_MODEL=os.getenv("SARVAM_CHAT_MODEL","sarvam-105b")
TTS_MODEL=os.getenv("SARVAM_TTS_MODEL","bulbul:v3")
SPEAKER=os.getenv("SARVAM_SPEAKER","shubh")

# Synthetic demo data. All amounts and customer histories are illustrative.
PRODUCTS=[
 {"id":"p1","name":"Milk 500ml","price":30,"stock":8,"reorder_at":15,"supplier":"Sri Lakshmi Distributors","unit":"pack","category":"Dairy"},
 {"id":"p2","name":"Bread","price":40,"stock":5,"reorder_at":12,"supplier":"Fresh Bake Supply","unit":"loaf","category":"Bakery"},
 {"id":"p3","name":"Atta 5kg","price":280,"stock":9,"reorder_at":10,"supplier":"Sri Lakshmi Distributors","unit":"bag","category":"Staples"},
 {"id":"p4","name":"Rice 1kg","price":68,"stock":42,"reorder_at":18,"supplier":"Sri Lakshmi Distributors","unit":"kg","category":"Staples"},
 {"id":"p5","name":"Eggs (6)","price":42,"stock":7,"reorder_at":12,"supplier":"Green Farm Foods","unit":"tray","category":"Dairy"},
 {"id":"p6","name":"Cooking Oil 1L","price":145,"stock":24,"reorder_at":10,"supplier":"Sri Lakshmi Distributors","unit":"bottle","category":"Staples"},
 {"id":"p7","name":"Toor Dal 1kg","price":165,"stock":4,"reorder_at":10,"supplier":"Sri Lakshmi Distributors","unit":"bag","category":"Staples"},
 {"id":"p8","name":"Biscuits","price":10,"stock":65,"reorder_at":20,"supplier":"Metro FMCG","unit":"packet","category":"Snacks"},
]
CUSTOMERS=[
 {"id":"C-104","name":"Anita","visits":8,"last_days":9,"usual":["Atta 5kg","Milk 500ml"],"opted_in":True,"avg_bill":310},
 {"id":"C-117","name":"Rahul","visits":12,"last_days":16,"usual":["Rice 1kg","Cooking Oil 1L"],"opted_in":True,"avg_bill":230},
 {"id":"C-121","name":"Sana","visits":6,"last_days":24,"usual":["Milk 500ml","Bread"],"opted_in":True,"avg_bill":95},
 {"id":"C-132","name":"Kiran","visits":4,"last_days":5,"usual":["Eggs (6)","Bread"],"opted_in":False,"avg_bill":85},
 {"id":"C-145","name":"Meena","visits":10,"last_days":31,"usual":["Toor Dal 1kg","Rice 1kg"],"opted_in":True,"avg_bill":260},
]
TRANSACTIONS=[
 {"id":"TX-901","time":"09:12","amount":389,"items":"Milk, Bread, Atta","status":"Paid"},
 {"id":"TX-902","time":"09:28","amount":145,"items":"Cooking Oil","status":"Paid"},
 {"id":"TX-903","time":"10:03","amount":82,"items":"Eggs, Biscuits","status":"Paid"},
 {"id":"TX-904","time":"10:41","amount":280,"items":"Atta 5kg","status":"Paid"},
 {"id":"TX-905","time":"11:06","amount":68,"items":"Rice 1kg","status":"Paid"},
]
OFFERS=[
 {"id":"OF-01","customer":"Anita","customer_id":"C-104","text":"Your atta is probably running low. Get ₹20 off your next Atta 5kg purchase this week.","discount":20,"item":"Atta 5kg","status":"Sent","control":False},
 {"id":"OF-02","customer":"Rahul","customer_id":"C-117","text":"Time to stock up on rice. Enjoy ₹10 cashback on Rice 1kg.","discount":10,"item":"Rice 1kg","status":"Redeemed","control":False},
 {"id":"OF-03","customer":"Sana","customer_id":"C-121","text":"Fresh bread and milk are waiting. Get ₹10 off your combo.","discount":10,"item":"Bread","status":"Sent","control":False},
]
STATE={"sales_today":12840,"sales_yesterday":11620,"transactions":42,"cashback_spent":320,"incremental_sales":3400,"offers_sent":18,"offers_redeemed":11,"orders_placed":0,"recent":TRANSACTIONS}

# Demo purchase-order history is persisted locally so it survives server restarts.
ORDER_FILE=BASE_DIR / "data" / "supplier_orders.json"
ORDER_FILE.parent.mkdir(parents=True, exist_ok=True)
def load_supplier_orders():
 try:
  data=json.loads(ORDER_FILE.read_text(encoding="utf-8"))
  return data if isinstance(data,list) else []
 except (FileNotFoundError, json.JSONDecodeError, OSError):
  return []
SUPPLIER_ORDERS=load_supplier_orders()
STATE["orders_placed"]=len(SUPPLIER_ORDERS)
def save_supplier_orders():
 ORDER_FILE.write_text(json.dumps(SUPPLIER_ORDERS,ensure_ascii=False,indent=2),encoding="utf-8")
 _db_sync_all()

def sarvam_headers():
 return {"api-subscription-key":SARVAM_KEY,"Content-Type":"application/json"}
async def chat(prompt, system="You are ShopMate AI, a concise and practical assistant for Indian kirana shop owners."):
 if not SARVAM_KEY: return None
 async with httpx.AsyncClient(timeout=35) as client:
  r=await client.post("https://api.sarvam.ai/v1/chat/completions",headers=sarvam_headers(),json={"model":CHAT_MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":500})
  if r.status_code>=400: raise HTTPException(502, f"Sarvam chat error: {r.text[:250]}")
  data=r.json()
  return data.get("choices",[{}])[0].get("message",{}).get("content")

@app.get("/",response_class=HTMLResponse)
def home():
 response=HTMLResponse((BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))
 response.headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
 response.headers["Pragma"]="no-cache"
 return response

@app.get("/api/version")
def app_version():
 return {"app":"ShopMate AI","build":"token-auth-reset-2026-11-14","source":"five-minute-bearer-sessions"}
@app.get("/api/dashboard")
def dashboard():
 _db_sync_all()
 low=[p for p in PRODUCTS if p["stock"]<=p["reorder_at"]]
 sent,redeemed,redemption_rate=_offer_metrics()
 paid_cashback=sum(int(x.get('cashback',0)) for x in DEMO.get('payments',[]))
 return {"shop":"Ramesh Kirana Store","location":"Hyderabad, Telangana","today":STATE["sales_today"],"yesterday":STATE["sales_yesterday"],"transactions":STATE["transactions"],"avg_bill":round(STATE["sales_today"]/max(1,STATE["transactions"])),"products":PRODUCTS,"low_stock":low,"customers":CUSTOMERS,"offers":DEMO.get('offers',[]),"recent":STATE["recent"],"impact":{"incremental_sales":sum(int(x.get('total_paid',0)) for x in DEMO.get('payments',[])),"cashback_spent":paid_cashback,"offers_sent":sent,"offers_redeemed":redeemed,"conversion":redemption_rate,"net_lift":sum(int(x.get('total_paid',0)) for x in DEMO.get('payments',[]))-paid_cashback}}

class BillRequest(BaseModel):
 transcript:str
 language:str="en-IN"
@app.post("/api/bill")
async def create_bill(body:BillRequest):
 text=body.transcript.strip()
 if not text: raise HTTPException(400,"Please say or enter at least one item.")
 prompt=("Extract kirana shopping items from this utterance. Match only this catalog and return JSON only as "
 '{"items":[{"product":"exact catalog product name","quantity":1}],"clarification":""}. '
 "If a product is not in catalog, put its name in clarification and do not invent a price. "
 "Catalog: "+json.dumps([{ "name":p["name"],"price":p["price"]} for p in PRODUCTS])+
 "\nUtterance: "+text)
 parsed=None
 if SARVAM_KEY:
  raw=await chat(prompt,"You extract structured shopping bills. Never invent catalog items or quantities.")
  try:
   m=re.search(r'\{.*\}',raw,re.S); parsed=json.loads(m.group(0)) if m else None
  except Exception: parsed=None
 # Deterministic multilingual parser is authoritative for catalog coverage.
 # Merge catalog matches with LLM output because the LLM can omit items.
 low=text.lower()
 aliases={
  "p1":["milk 500ml","milk","paalu","పాలు","మిల్క్"],
  "p2":["bread","బ్రెడ్"],
  "p3":["atta 5kg","atta","aata","flour","పిండి","ఆటా"],
  "p4":["rice 1kg","rice","biyyam","బియ్యం","రైస్"],
  "p5":["eggs (6)","eggs","egg","గుడ్లు","ఎగ్స్"],
  "p6":["cooking oil 1l","cooking oil","oil","నూనె","ఆయిల్"],
  "p7":["toor dal 1kg","toor dal","dal","pappu","పప్పు","కందిపప్పు"],
  "p8":["biscuits","biscuit","బిస్కెట్లు","బిస్కట్"]}
 number_words={"one":1,"a":1,"an":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"ఒక":1,"ఒక్క":1,"రెండు":2,"మూడు":3,"నాలుగు":4,"ఐదు":5,"ఆరు":6,"ఏడు":7,"ఎనిమిది":8}
 segments=[x.strip() for x in re.split(r'[,;\n]|\band\b',low) if x.strip()]
 deterministic=[]
 for prod in PRODUCTS:
  keys=aliases.get(prod['id'],[prod['name'].lower()]); found=[]
  for seg in segments:
   key=next((k for k in sorted(keys,key=len,reverse=True) if k and k in seg),None)
   if not key: continue
   prefix=seg[:seg.find(key)].strip()
   nums=re.findall(r'(?<![\w.])(\d+)(?!\s*(?:kg|కేజీ|కిలో))',prefix)
   qty=int(nums[-1]) if nums else 1
   if not nums:
    for word,n in number_words.items():
     if re.search(re.escape(word),prefix): qty=n
   found.append(max(1,min(50,qty)))
  if found: deterministic.append({"product":prod['name'],"quantity":sum(found)})
 merged={x['product'].lower():x for x in deterministic}
 if isinstance(parsed,dict):
  for it in parsed.get('items',[]):
   name=str(it.get('product','')).lower()
   if name and name not in merged: merged[name]={'product':it.get('product'),'quantity':it.get('quantity',1)}
 parsed={'items':list(merged.values()),'clarification':'' if merged else 'I could not identify the items. Please try again or add them manually.'}
 clean=[]
 for it in parsed.get("items",[]) if isinstance(parsed,dict) else []:
  p=next((x for x in PRODUCTS if x["name"].lower()==str(it.get("product","")).lower()),None)
  if not p: continue
  try:q=max(1,min(50,int(it.get("quantity",1))))
  except:q=1
  clean.append({"id":p["id"],"name":p["name"],"quantity":q,"unit_price":p["price"],"total":q*p["price"]})
 if not clean:
  return {"ok":False,"transcript":text,"items":[],"total":0,"clarification":(parsed or {}).get("clarification") or "I couldn't match those items. Please try again or choose a product manually."}
 total=sum(i["total"] for i in clean)
 return {"ok":True,"transcript":text,"items":clean,"subtotal":total,"discount":0,"total":total,"currency":"INR","payment_qr":"demo://pay?merchant=RameshKirana&amount="+str(total),"note":"Bill draft only. Sales and stock update after the merchant confirms the demo payment."}
@app.post("/api/offers/generate")
async def generate_offers():
 results=[]
 for c in CUSTOMERS:
  if not c["opted_in"] or c["last_days"]<14: continue
  user=next((u for u in DEMO_USERS.values() if u.get('customer_id')==c['id']),None)
  if not user or not DEMO.get('consent',{}).get(c['id'],user.get('opted_in',False)): continue
  item=(c.get('usual') or ['Milk 500ml'])[0]
  product=next((p for p in PRODUCTS if p['name']==item),PRODUCTS[0])
  amount=20 if product['price']>=100 else 10
  text=f"You usually buy {item}. It may be time to restock — get ₹{amount} cashback on your next purchase at Ramesh Kirana this week."
  if SARVAM_KEY:
   suggestion=await chat(f"Write one warm, short customer offer in English for this customer. Item: {item}. Benefit: ₹{amount} cashback. Keep it under 22 words. Do not invent facts.")
   if suggestion: text=suggestion.strip().strip('"')
  if any(o.get('customer_id')==c['id'] and o.get('product_id')==product['id'] and not o.get('redeemed') for o in DEMO.get('offers',[])): continue
  oid=f"SHOP-OF-{DEMO['next_offer']:04d}"; DEMO['next_offer']+=1
  offer={'id':oid,'customer_id':c['id'],'customer':c['name'],'product_id':product['id'],'product':product['name'],'cashback':amount,'message':text,'status':'Sent to ShopMate inbox (demo)','created_at':datetime.now().astimezone().isoformat(timespec='seconds'),'redeemed':False,'triggered_by':'Personalized offer generator'}
  DEMO['offers'].insert(0,offer); DEMO['notifications'].setdefault(c['id'],[]).insert(0,{'id':oid,'title':'New offer from Ramesh Kirana','message':text,'cashback':amount,'product':product['name'],'created_at':offer['created_at'],'read':False})
  results.append(offer); _event('offer_received',{'customer_id':c['id'],'customer':c['name'],'offer_id':oid,'message':text})
 _demo_save(); _db_sync_all()
 return {"offers":results,"message":f"Generated {len(results)} consent-based offers and delivered them to customer ShopMate inboxes. Customers without opt-in were skipped."}

@app.get("/api/restock")
def restock():
 rec=[]
 for p in PRODUCTS:
  if p["stock"]<=p["reorder_at"]:
   target=max(p["reorder_at"]*2,20)
   qty=max(0,target-p["stock"])
   rec.append({**p,"suggested_qty":qty,"estimated_cost":qty*p["price"],"reason":"Stock is at or below reorder threshold"})
 return {"recommendations":rec,"total_estimated_cost":sum(x["estimated_cost"] for x in rec),"orders":SUPPLIER_ORDERS}

@app.get("/api/restock/orders")
def supplier_order_history():
 return {"orders":SUPPLIER_ORDERS,"total":len(SUPPLIER_ORDERS)}

class OrderRequest(BaseModel):
 product_id:str
 quantity:int

@app.post("/api/restock/order")
def place_order(body:OrderRequest):
 p=next((p for p in PRODUCTS if p["id"]==body.product_id),None)
 if not p: raise HTTPException(404,"Product not found")
 if body.quantity<1 or body.quantity>500: raise HTTPException(400,"Quantity must be between 1 and 500")
 STATE["orders_placed"]+=1
 order={
  "order_id":f"PO-DEMO-{datetime.now().strftime('%Y%m%d')}-{STATE['orders_placed']:03d}",
  "supplier":p["supplier"],"product_id":p["id"],"product":p["name"],
  "quantity":body.quantity,"unit":p["unit"],"unit_price":p["price"],
  "estimated_cost":body.quantity*p["price"],
  "created_at":datetime.now().astimezone().isoformat(timespec="seconds"),
  "status":"Created (demo)",
  "status_note":"Purchase order recorded in ShopMate demo. It has NOT been transmitted to the supplier.",
  "transmission":"Not sent"
 }
 SUPPLIER_ORDERS.insert(0,order)
 save_supplier_orders()
 return {"ok":True,"message":f"Demo purchase order {order['order_id']} created for {p['supplier']}.",**order}

class OrderStatusRequest(BaseModel):
 status:str

@app.patch("/api/restock/orders/{order_id}")
def update_supplier_order(order_id:str,body:OrderStatusRequest):
 # The UI historically sent bare values (e.g. "Delivered"), while stored
 # orders use the canonical "(demo)" suffix. Accept both formats so older
 # browser tabs and cached frontends continue to work.
 status_aliases={
  "created":"Created (demo)",
  "created (demo)":"Created (demo)",
  "confirmed":"Confirmed (demo)",
  "confirmed (demo)":"Confirmed (demo)",
  "dispatched":"Dispatched (demo)",
  "dispatched (demo)":"Dispatched (demo)",
  "delivered":"Delivered (demo)",
  "delivered (demo)":"Delivered (demo)",
  "cancelled":"Cancelled (demo)",
  "cancelled (demo)":"Cancelled (demo)",
  "canceled":"Cancelled (demo)",
  "canceled (demo)":"Cancelled (demo)"
 }
 normalized_status=status_aliases.get(body.status.strip().casefold())
 if not normalized_status:
  raise HTTPException(400,"Invalid order status. Choose Created, Confirmed, Dispatched, Delivered, or Cancelled.")
 order=next((o for o in SUPPLIER_ORDERS if o["order_id"]==order_id),None)
 if not order: raise HTTPException(404,"Supplier order not found")
 # Receiving stock is an inventory event: apply it exactly once when the
 # order first reaches Delivered. Repeated updates must not double-count it.
 if order.get("stock_received") and normalized_status != "Delivered (demo)":
  raise HTTPException(400,"This order has already been received. Inventory was updated and the delivered status is locked.")
 if normalized_status == "Delivered (demo)" and not order.get("stock_received", False):
  product=next((p for p in PRODUCTS if p["id"]==order["product_id"]),None)
  if not product:
   raise HTTPException(404,"Product linked to this order was not found")
  product["stock"] += order["quantity"]
  order["stock_received"] = True
  order["stock_received_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
  order["stock_before_receipt"] = product["stock"] - order["quantity"]
  order["stock_after_receipt"] = product["stock"]
  order["status_note"] = f"Demo delivery marked received. Inventory increased by {order['quantity']} {order['unit']}(s), from {order['stock_before_receipt']} to {order['stock_after_receipt']}. This is a simulated receipt, not a supplier confirmation."
 else:
  order["status_note"]="Status manually updated for demonstration only. No supplier acknowledgement or shipment event was received."
 order["status"]=normalized_status
 order["updated_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
 save_supplier_orders()
 return {"ok":True,"order":order,"products":PRODUCTS,"message":("Demo delivery recorded and inventory updated." if order.get("stock_received") else "Demo order status updated.")}

@app.get("/api/brief")
async def daily_brief(language:str="en"):
 _db_sync_all()
 low=[p for p in PRODUCTS if p["stock"]<=p["reorder_at"]]
 churn=[c for c in CUSTOMERS if c["last_days"]>=21 and c["opted_in"] and DEMO.get('consent',{}).get(c['id'],c.get('opted_in',False)) and any(u.get('customer_id')==c['id'] for u in DEMO_USERS.values())]
 sent=len(DEMO.get('offers',[])); redeemed=sum(1 for o in DEMO.get('offers',[]) if o.get('redeemed'))
 summary=f"Good morning. Today's recorded sales are ₹{STATE['sales_today']:,} across {STATE['transactions']} transactions. {len(low)} products need restocking. {len(churn)} opted-in customers are at risk of becoming inactive. {sent} offers have been sent and {redeemed} redeemed. Recommended action: create demo purchase orders for low stock and send cashback offers to at-risk opted-in customers."
 if SARVAM_KEY:
  out=await chat(f"Rewrite this merchant briefing in {'Telugu' if language=='te' else 'simple English'}, friendly spoken style, under 75 words. Preserve all numbers and facts: {summary}")
  if out: summary=out
 return {"brief":summary,"priority":"Restock and retain customers" if low or churn else "Review today's sales","low_stock_count":len(low),"at_risk_customers":len(churn),"offers_sent":sent,"offers_redeemed":redeemed,"actions":{"restock_products":[p['id'] for p in low],"at_risk_customers":[c['id'] for c in churn]}}

@app.post('/api/brief/take-action')
def take_brief_action():
 low=[p for p in PRODUCTS if p['stock']<=p['reorder_at']]
 at_risk=[c for c in CUSTOMERS if c['last_days']>=21 and c['opted_in'] and DEMO.get('consent',{}).get(c['id'],c.get('opted_in',False)) and any(u.get('customer_id')==c['id'] for u in DEMO_USERS.values())]
 created=[]; sent=[]
 for p in low:
  target=max(p['reorder_at']*2,20); qty=max(1,target-p['stock'])
  existing=next((o for o in SUPPLIER_ORDERS if o.get('product_id')==p['id'] and o.get('status') not in {'Delivered (demo)','Cancelled (demo)'}),None)
  if existing: continue
  STATE['orders_placed']+=1
  order={'order_id':f"PO-DEMO-{datetime.now().strftime('%Y%m%d')}-{STATE['orders_placed']:03d}",'supplier':p['supplier'],'product_id':p['id'],'product':p['name'],'quantity':qty,'unit':p['unit'],'unit_price':p['price'],'estimated_cost':qty*p['price'],'created_at':datetime.now().astimezone().isoformat(timespec='seconds'),'status':'Created (demo)','status_note':'Automatically created by Daily Briefing. Review before treating as a real supplier order.','transmission':'Not sent','triggered_by':'Daily Briefing'}
  SUPPLIER_ORDERS.insert(0,order); created.append(order)
 save_supplier_orders()
 for c in at_risk:
  # Avoid duplicate active retention cashback offers for the same customer.
  if any(o.get('customer_id')==c['id'] and not o.get('redeemed') and not o.get('reserved_bill_id') and o.get('triggered_by')=='Daily Briefing' for o in DEMO.get('offers',[])): continue
  item=(c.get('usual') or ['Milk 500ml'])[0]
  product=next((p for p in PRODUCTS if p['name']==item),PRODUCTS[0])
  amount=20 if product['price']>=100 else 10
  username=next((u for u in DEMO_USERS.values() if u.get('customer_id')==c['id']),{})
  oid=f"SHOP-OF-{DEMO['next_offer']:04d}"; DEMO['next_offer']+=1
  msg=f"We miss you at Ramesh Kirana! Enjoy ₹{amount} cashback on {product['name']} on your next purchase."
  offer={'id':oid,'customer_id':c['id'],'customer':c['name'],'product_id':product['id'],'product':product['name'],'cashback':amount,'message':msg,'status':'Sent to ShopMate inbox (demo)','created_at':datetime.now().astimezone().isoformat(timespec='seconds'),'redeemed':False,'triggered_by':'Daily Briefing'}
  DEMO['offers'].insert(0,offer); DEMO['notifications'].setdefault(c['id'],[]).insert(0,{'id':oid,'title':'A cashback offer from Ramesh Kirana','message':msg,'cashback':amount,'product':product['name'],'created_at':offer['created_at'],'read':False})
  sent.append(offer)
 _event('brief_actions_executed',{'orders':[x['order_id'] for x in created],'offers':[x['id'] for x in sent]})
 _demo_save(); _db_sync_all()
 return {'ok':True,'orders_created':created,'offers_sent':sent,'message':f"Created {len(created)} demo restock orders and sent {len(sent)} cashback offers to opted-in at-risk customers. No external supplier or SMS/WhatsApp messages were sent."}

@app.post('/api/checklist')
def save_checklist(body:dict):
 checks=body.get('checks',[])
 _db_log('cash_leak_checklist','shift-verification',{'checks':checks,'completed_at':datetime.now().astimezone().isoformat(timespec='seconds')})
 return {'ok':True,'saved':len(checks),'message':'Verification checklist saved to the ShopMate SQLite activity log.'}

@app.post("/api/voice/transcribe")
async def transcribe(file:UploadFile=File(...),language_code:str=Form("te-IN")):
 if not SARVAM_KEY: raise HTTPException(503,"Add SARVAM_API_KEY to .env to enable live voice transcription.")
 raw=await file.read()
 if len(raw)>10*1024*1024: raise HTTPException(413,"Audio file must be under 10 MB")
 content_type=(file.content_type or "").split(";")[0].strip().lower()
 if content_type not in {"audio/wav","audio/x-wav","audio/mpeg","audio/mp3","audio/pcm_s16le"}:
  raise HTTPException(415,"Unsupported audio format. ShopMate sends 16 kHz PCM WAV to Sarvam; please refresh the page and record again.")
 async with httpx.AsyncClient(timeout=60) as client:
  r=await client.post("https://api.sarvam.ai/speech-to-text",headers={"api-subscription-key":SARVAM_KEY},data={"model":"saaras:v4","mode":"transcribe","language_code":language_code},files={"file":(file.filename or "shopmate-order.wav",raw,content_type)})
  if r.status_code>=400: raise HTTPException(502,"Sarvam speech-to-text failed: "+r.text[:250])
  return {"transcript":r.json().get("transcript",""),"language_code":language_code,"provider":"Sarvam Saaras v4"}
class SpeakRequest(BaseModel):
 text:str
 language_code:str="te-IN"
@app.post("/api/voice/speak")
async def speak(body:SpeakRequest):
 if not SARVAM_KEY: raise HTTPException(503,"Add SARVAM_API_KEY to .env to enable live speech.")
 async with httpx.AsyncClient(timeout=60) as client:
  r=await client.post("https://api.sarvam.ai/text-to-speech",headers=sarvam_headers(),json={"text":body.text[:2400],"target_language_code":body.language_code,"speaker":SPEAKER,"model":TTS_MODEL,"output_audio_codec":"mp3"})
  if r.status_code>=400: raise HTTPException(502,"Sarvam text-to-speech failed: "+r.text[:250])
  audios=r.json().get("audios",[])
  if not audios: raise HTTPException(502,"Sarvam returned no audio")
  return Response(content=base64.b64decode(audios[0]),media_type="audio/mpeg")
@app.get("/api/impact")
def impact():
 _db_sync_all()
 sent=len(DEMO.get('offers',[])); redeemed=sum(1 for o in DEMO.get('offers',[]) if o.get('redeemed'))
 cashback=sum(int(p.get('cashback',0)) for p in DEMO.get('payments',[]))
 attributable=sum(int(p.get('total_paid',0)) for p in DEMO.get('payments',[]) if p.get('cashback',0)>0)
 return {"incremental_sales":attributable,"cashback_spent":cashback,"net_lift":attributable-cashback,"offers_sent":sent,"offers_redeemed":redeemed,"conversion":round(redeemed/max(1,sent)*100,1),"control_group":{"customers":0,"repeat_rate":0},"offer_group":{"customers":len({o.get('customer_id') for o in DEMO.get('offers',[])}),"repeat_rate":0},"disclaimer":"Live ShopMate demo ledger totals. This is not a causal incrementality estimate or Paytm campaign result."}

@app.get("/api/health")
def health(): return {"ok":True,"sarvam_configured":bool(SARVAM_KEY),"chat_model":CHAT_MODEL,"speech":"Saaras v4","tts":TTS_MODEL}


# ---------- Merchant / customer demo experience (inspired by Munshi AI) ----------
# Persistent local demo state. This is a prototype ledger, not a Paytm integration.
DEMO_FILE=BASE_DIR / "data" / "merchant_customer_demo.json"
DEMO_FILE.parent.mkdir(parents=True, exist_ok=True)
DB_FILE=BASE_DIR / "data" / "shopmate.db"

def _db_conn():
 conn=sqlite3.connect(DB_FILE, timeout=20)
 conn.row_factory=sqlite3.Row
 conn.execute("PRAGMA journal_mode=WAL")
 conn.execute("PRAGMA foreign_keys=ON")
 return conn

def _db_init():
 with _db_conn() as conn:
  conn.execute("CREATE TABLE IF NOT EXISTS entity_records (entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(entity_type, entity_id))")
  conn.execute("CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, entity_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
  conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(event_type, created_at)")
  conn.execute("CREATE TABLE IF NOT EXISTS offers (offer_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, redeemed INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
  conn.execute("CREATE TABLE IF NOT EXISTS bills (bill_id TEXT PRIMARY KEY, status TEXT NOT NULL, customer_id TEXT, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
  conn.execute("CREATE TABLE IF NOT EXISTS payments (payment_id TEXT PRIMARY KEY, bill_id TEXT, customer_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
  conn.execute("CREATE TABLE IF NOT EXISTS notifications (notification_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")

def _db_put(conn, kind, key, value):
 conn.execute("INSERT INTO entity_records(entity_type,entity_id,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(entity_type,entity_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",(kind,str(key),json.dumps(value,ensure_ascii=False),datetime.now().astimezone().isoformat(timespec='seconds')))

def _db_sync_all():
 # A normalized entity ledger keeps every dashboard's source records durable in one SQLite database.
 try:
  with _db_conn() as conn:
   collections={
    'product':[(x['id'],x) for x in PRODUCTS],
    'customer':[(x['id'],x) for x in CUSTOMERS],
    'user':[(k,v) for k,v in DEMO_USERS.items()],
    'offer':[(x['id'],x) for x in DEMO.get('offers',[])],
    'bill':[(x['bill_id'],x) for x in DEMO.get('pending_bills',[])],
    'payment':[(x['payment_id'],x) for x in DEMO.get('payments',[])],
    'notification':[(f"{cid}:{n.get('id',i)}",n) for cid,items in DEMO.get('notifications',{}).items() for i,n in enumerate(items)],
    'event':[(x['id'],x) for x in DEMO.get('events',[])],
    'supplier_order':[(x['order_id'],x) for x in SUPPLIER_ORDERS],
    'consent':[(k,{'customer_id':k,'opted_in':v}) for k,v in DEMO.get('consent',{}).items()],
    'state':[('merchant',STATE)],
    'meta':[('counters',{k:v for k,v in DEMO.items() if k not in {'offers','payments','pending_bills','events','notifications','consent'}})]
   }
   for kind, rows in collections.items():
    for key,value in rows: _db_put(conn,kind,key,value)
 except Exception as exc:
  print('SQLite sync warning:',exc)

def _db_log(event_type, entity_id, payload):
 with _db_conn() as conn:
  conn.execute("INSERT INTO activity_log(event_type,entity_id,payload,created_at) VALUES(?,?,?,?)",(event_type,str(entity_id or ''),json.dumps(payload,ensure_ascii=False),datetime.now().astimezone().isoformat(timespec='seconds')))

DEMO_USERS={
 "merchant":{"role":"merchant","name":"Ramesh Store","pin":"1111"},
 "anita":{"role":"customer","name":"Anita","customer_id":"C-104","pin":"2222","opted_in":True},
 "rahul":{"role":"customer","name":"Rahul","customer_id":"C-117","pin":"3333","opted_in":True},
 "sana":{"role":"customer","name":"Sana","customer_id":"C-121","pin":"4444","opted_in":True},
 "kiran":{"role":"customer","name":"Kiran","customer_id":"C-132","pin":"5555","opted_in":False},
}

# Immutable prototype seed: reset returns to these illustrative records only.
PROTOTYPE_PRODUCTS=copy.deepcopy(PRODUCTS)
PROTOTYPE_CUSTOMERS=copy.deepcopy(CUSTOMERS)
PROTOTYPE_USERS=copy.deepcopy(DEMO_USERS)
PROTOTYPE_STATE={"sales_today":12840,"sales_yesterday":11620,"transactions":42,"cashback_spent":320,"incremental_sales":3400,"offers_sent":18,"offers_redeemed":11,"orders_placed":0,"recent":copy.deepcopy(TRANSACTIONS)}
def _demo_default():
 return {"offers":[],"payments":[],"pending_bills":[],"events":[],"next_bill":1,"next_event":1,"next_offer":1,"next_payment":1,"consent":{},
         "notifications":{u:[] for u in ["C-104","C-117","C-121","C-132"]}}
def _demo_load():
 try:
  d=json.loads(DEMO_FILE.read_text(encoding='utf-8'))
  base=_demo_default(); base.update(d)
  base.setdefault("consent", {})
  for key, value in _demo_default().items(): base.setdefault(key, value)
  if d.get('customers'): CUSTOMERS[:] = d['customers']
  if d.get('users'): DEMO_USERS.update(d['users'])
  for k in base['notifications']: base['notifications'].setdefault(k,[])
  return base
 except Exception: return _demo_default()
DEMO=_demo_load()
_db_init()
def _demo_save():
 data=dict(DEMO); data['customers']=CUSTOMERS; data['users']=DEMO_USERS
 DEMO_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 _db_sync_all()
def _db_restore():
 # SQLite wins after the first migration; the legacy JSON file is retained as a one-time import/backup.
 try:
  with _db_conn() as conn:
   rows=conn.execute("SELECT entity_type,entity_id,payload FROM entity_records").fetchall()
  if not rows: return
  grouped={}
  for row in rows:
   try: grouped.setdefault(row['entity_type'],{})[row['entity_id']]=json.loads(row['payload'])
   except Exception: pass
  if 'state' in grouped and 'merchant' in grouped['state']: STATE.update(grouped['state']['merchant'])
  for kind,target,key in [('product',PRODUCTS,'id'),('customer',CUSTOMERS,'id')]:
   if grouped.get(kind): target[:]=list(grouped[kind].values())
  if grouped.get('user'): DEMO_USERS.update(grouped['user'])
  if grouped.get('offer'): DEMO['offers']=list(grouped['offer'].values())
  if grouped.get('bill'): DEMO['pending_bills']=list(grouped['bill'].values())
  if grouped.get('payment'): DEMO['payments']=list(grouped['payment'].values())
  if grouped.get('event'): DEMO['events']=sorted(grouped['event'].values(),key=lambda x:x.get('id',0))[-250:]
  if grouped.get('supplier_order'): SUPPLIER_ORDERS[:]=list(grouped['supplier_order'].values())
  if grouped.get('consent'): DEMO['consent']={k:v.get('opted_in',False) for k,v in grouped['consent'].items()}
  if grouped.get('notification'):
   notifications={}
   for compound,item in grouped['notification'].items():
    cid=compound.split(':',1)[0]; notifications.setdefault(cid,[]).append(item)
   for cid,items in notifications.items(): DEMO.setdefault('notifications',{})[cid]=sorted(items,key=lambda x:x.get('created_at',''),reverse=True)
  if grouped.get('meta') and 'counters' in grouped['meta']:
   counters=grouped['meta']['counters']
   for k,v in counters.items(): DEMO[k]=v
 except Exception as exc: print('SQLite restore warning:',exc)

_db_restore()
_db_sync_all()

def _reconcile_demo_offers():
 # Repair legacy/demo records where the customer notification survived but its offer
 # entity was not written to the merchant ledger. SHOP-OF IDs are the canonical offer IDs.
 offers=DEMO.setdefault('offers',[])
 by_id={str(o.get('id')):o for o in offers if o.get('id')}
 customers={c.get('id'):c for c in CUSTOMERS}
 users={u.get('customer_id'):u for u in DEMO_USERS.values() if u.get('customer_id')}
 for cid,items in DEMO.setdefault('notifications',{}).items():
  for n in items:
   oid=str(n.get('id',''))
   if not oid.startswith('SHOP-OF-') and not ('offer' in str(n.get('title','')).lower() and ('cashback' in n or 'product' in n)): continue
   offer=by_id.get(oid)
   if offer is None:
    user=users.get(cid,{})
    customer=customers.get(cid,{})
    offer={'id':oid,'customer_id':cid,'customer':user.get('name') or customer.get('name') or 'Customer',
           'product':n.get('product',''),'cashback':int(n.get('cashback',0) or 0),
           'message':n.get('message',''),'created_at':n.get('created_at',''),
           'status':n.get('status') or ('Redeemed' if n.get('redeemed') else 'Sent to ShopMate inbox (demo)'),
           'redeemed':bool(n.get('redeemed'))}
    offers.append(offer); by_id[oid]=offer
   if n.get('redeemed') or 'redeemed' in str(n.get('status','')).lower():
    offer['redeemed']=True
    offer['status']=n.get('status') or 'Redeemed'
    offer['redeemed_bill_id']=n.get('redeemed_bill_id') or offer.get('redeemed_bill_id')
   if n.get('reserved_bill_id') and not offer.get('redeemed'):
    offer['reserved_bill_id']=n['reserved_bill_id']
 # Normalize legacy status strings and counters.
 for o in offers:
  if 'redeemed' in str(o.get('status','')).lower(): o['redeemed']=True
  if o.get('redeemed'):
   o['reserved_bill_id']=None
 ids=[int(m.group(1)) for o in offers if (m:=re.search(r'SHOP-OF-(\\d+)',str(o.get('id',''))))]
 if ids: DEMO['next_offer']=max(int(DEMO.get('next_offer',1)),max(ids)+1)
 return offers

def _offer_metrics():
 offers=_reconcile_demo_offers()
 sent=len({str(o.get('id')) for o in offers if o.get('id')})
 redeemed=len({str(o.get('id')) for o in offers if o.get('id') and (bool(o.get('redeemed')) or 'redeemed' in str(o.get('status','')).lower())})
 return sent,redeemed,round(redeemed/max(1,sent)*100,1)

_reconcile_demo_offers()
_db_sync_all()

def _event(kind,payload):
 ev={"id":DEMO["next_event"],"type":kind,"at":datetime.now().astimezone().isoformat(timespec='seconds'),**payload}
 DEMO["next_event"]+=1; DEMO["events"].append(ev); DEMO["events"]=DEMO["events"][-250:]; _demo_save(); _db_log(kind,payload.get('bill_id') or payload.get('offer_id') or (payload.get('payment') or {}).get('payment_id'),ev); return ev
class DemoLogin(BaseModel): username:str; pin:str
@app.post('/api/demo/login')
def demo_login(body:DemoLogin):
 u=DEMO_USERS.get(body.username.lower().strip())
 if not u or u['pin']!=body.pin: raise HTTPException(401,'Invalid demo username or PIN')
 token=secrets.token_urlsafe(36); expires=time.time()+SESSION_TTL_SECONDS
 SESSIONS[token]={'username':body.username.lower().strip(),'role':u['role'],'expires_at':expires}
 out={k:v for k,v in u.items() if k!='pin'}
 out['opted_in']=DEMO.get('consent',{}).get(u.get('customer_id'),u.get('opted_in',False))
 return {'token':token,'token_type':'Bearer','expires_in':SESSION_TTL_SECONDS,'user':out}
@app.post('/api/demo/logout')
def demo_logout(request:Request):
 auth=request.headers.get('authorization',''); token=auth[7:].strip() if auth.lower().startswith('bearer ') else ''
 SESSIONS.pop(token,None)
 return {'ok':True,'message':'Session revoked'}
@app.get('/api/demo/me')
def demo_me(request:Request):
 username=request.state.session['username']; u=DEMO_USERS.get(username)
 if not u: raise HTTPException(404,'Demo user not found')
 out={k:v for k,v in u.items() if k!='pin'}
 out['opted_in']=DEMO.get('consent',{}).get(u.get('customer_id'),u.get('opted_in',False))
 return out
@app.post('/api/demo/consent')
def demo_consent(body:dict, request:Request):
 username=request.state.session['username']; u=DEMO_USERS.get(username)
 if not u or u['role']!='customer': raise HTTPException(403,'Customer login required')
 opted=bool(body.get('opted_in',False)); DEMO.setdefault('consent',{})[u['customer_id']]=opted
 customer=next((c for c in CUSTOMERS if c['id']==u['customer_id']),None)
 if customer: customer['opted_in']=opted
 _demo_save()
 return {'ok':True,'opted_in':opted}
@app.get('/api/demo/catalog')
def demo_catalog(): return {"products":[{k:p[k] for k in ('id','name','price','stock','unit','category')} for p in PRODUCTS]}
@app.get('/api/demo/offers')
def demo_offers(request:Request):
 u=DEMO_USERS.get(request.state.session['username'])
 if not u or u['role']!='customer': raise HTTPException(403,'Customer login required')
 cid=u['customer_id']
 customer_offers=[o for o in DEMO['offers'] if o['customer_id']==cid]
 customer_payments=[p for p in DEMO.get('payments',[]) if p.get('customer_id')==cid]
 return {"offers":customer_offers,"payments":customer_payments,"notifications":DEMO['notifications'].get(cid,[]),"opted_in":DEMO.get('consent',{}).get(cid,u['opted_in']),"cashback_available":sum(int(o.get('cashback',0)) for o in customer_offers if not o.get('redeemed') and not o.get('reserved_bill_id')),"cashback_used":sum(int(p.get('cashback',0)) for p in customer_payments)}
class DemoOfferIn(BaseModel): customer_id:str; product_id:str; cashback:int; message:str=''
@app.post('/api/demo/offers/send')
def demo_send_offer(body:DemoOfferIn):
 c=next((x for x in CUSTOMERS if x['id']==body.customer_id),None)
 u=next((x for x in DEMO_USERS.values() if x.get('customer_id')==body.customer_id),None)
 p=next((x for x in PRODUCTS if x['id']==body.product_id),None)
 if not c or not u or not p: raise HTTPException(404,'Customer or product not found')
 if not DEMO.get('consent',{}).get(body.customer_id,u['opted_in']): raise HTTPException(403,'This customer has not opted in to promotional offers')
 if body.cashback<1 or body.cashback>500: raise HTTPException(400,'Cashback must be between ₹1 and ₹500')
 msg=body.message.strip() or f"Enjoy ₹{body.cashback} cashback on {p['name']} on your next purchase at Ramesh Kirana!"
 oid=f"SHOP-OF-{DEMO['next_offer']:04d}"; DEMO['next_offer']+=1
 offer={"id":oid,"customer_id":body.customer_id,"customer":u['name'],"product_id":p['id'],"product":p['name'],"cashback":body.cashback,"message":msg,"status":"Sent to ShopMate inbox (demo)","created_at":datetime.now().astimezone().isoformat(timespec='seconds'),"redeemed":False}
 DEMO['offers'].insert(0,offer)
 notification={"id":oid,"title":"New offer from Ramesh Kirana","message":msg,"cashback":body.cashback,"product":p['name'],"created_at":offer['created_at'],"read":False}
 DEMO['notifications'].setdefault(body.customer_id,[]).insert(0,notification)
 _demo_save()
 _event('offer_received',{"customer_id":body.customer_id,"customer":u['name'],"offer_id":oid,"message":msg})
 return {"ok":True,"offer":offer,"message":f"Offer delivered to {u['name']}'s ShopMate customer inbox (demo)."}
class MerchantBillConfirm(BaseModel):
 items:list[dict]
 customer_id:Optional[str]=None
 payment_mode:str="UPI (demo)"
@app.post('/api/demo/merchant/confirm-bill')
def merchant_confirm_bill(body:MerchantBillConfirm):
 if not body.items: raise HTTPException(400,'There are no items in this bill')
 customer=next((c for c in CUSTOMERS if c['id']==body.customer_id),None) if body.customer_id else None
 if body.customer_id and not customer: raise HTTPException(404,'Selected customer not found')
 clean=[]; subtotal=0
 for it in body.items:
  pid=str(it.get('id') or it.get('product_id') or '')
  p=next((x for x in PRODUCTS if x['id']==pid),None)
  if not p: raise HTTPException(400,'Unknown product in bill')
  try: q=int(it.get('quantity',0))
  except: q=0
  if q<1 or q>50: raise HTTPException(400,'Quantity must be between 1 and 50')
  if p['stock']<q: raise HTTPException(400,f"Only {p['stock']} {p['unit']}(s) of {p['name']} available")
  clean.append({"product_id":p['id'],"name":p['name'],"quantity":q,"unit":p['unit'],"unit_price":p['price'],"total":p['price']*q})
  subtotal+=p['price']*q
 # Redeem at most one eligible offer belonging to the identified, opted-in customer.
 redeemed_offer=None; cashback=0
 if customer and DEMO.get('consent',{}).get(customer['id'],customer['opted_in']):
  for offer in DEMO['offers']:
   if offer['customer_id']==customer['id'] and not offer['redeemed'] and offer['product_id'] in [x['product_id'] for x in clean]:
    cashback=min(int(offer['cashback']),subtotal); offer['redeemed']=True; offer['status']='Redeemed'; redeemed_offer=offer; break
 for item in clean:
  p=next(x for x in PRODUCTS if x['id']==item['product_id']); p['stock']-=item['quantity']
 pid=f"SHOP-TX-{DEMO['next_payment']:05d}"; DEMO['next_payment']+=1
 customer_name=customer['name'] if customer else 'Walk-in customer'
 payment={"payment_id":pid,"customer":customer_name,"customer_id":customer['id'] if customer else None,"items":clean,"subtotal":subtotal,"cashback":cashback,"total_paid":max(0,subtotal-cashback),"payment_mode":body.payment_mode,"status":"Paid (demo)","created_at":datetime.now().astimezone().isoformat(timespec='seconds')}
 DEMO['payments'].insert(0,payment)
 STATE['sales_today']+=payment['total_paid']; STATE['transactions']+=1
 STATE['recent'].insert(0,{"id":pid,"time":datetime.now().strftime('%H:%M'),"amount":payment['total_paid'],"items":', '.join(f"{x['quantity']} {x['name']}" for x in clean),"status":"Paid (demo)"}); STATE['recent']=STATE['recent'][:8]
 announcement=f"Payment received. Rupees {payment['total_paid']}. Thank you."
 ev=_event('payment_received',{"payment":payment,"soundbox_text":announcement})
 if redeemed_offer: _event('offer_redeemed',{"offer_id":redeemed_offer['id'],"customer":customer_name,"cashback":cashback})
 _demo_save()
 return {"ok":True,"payment":payment,"soundbox_text":announcement,"event_id":ev['id'],"message":"Merchant-confirmed demo sale recorded. Inventory, dashboard and Soundbox event updated."}

class PendingBillIn(BaseModel):
 items:list[dict]
 customer_id:Optional[str]=None
@app.get('/api/demo/customers')
def demo_customers():
 return {"customers":[{"id":c['id'],"name":c['name'],"opted_in":DEMO.get('consent',{}).get(c['id'],c.get('opted_in',False))} for c in CUSTOMERS]}
class CustomerRegister(BaseModel):
 name:str
 pin:str
 opted_in:bool=False
@app.post('/api/demo/register')
def demo_register(body:CustomerRegister):
 name=body.name.strip()
 if len(name)<2 or len(body.pin)<4: raise HTTPException(400,'Enter a name and a PIN of at least 4 digits')
 base='customer_'+''.join(ch.lower() for ch in name if ch.isalnum())
 username=base; n=2
 while username in DEMO_USERS:
  username=f'{base}{n}'; n+=1
 cid=f'C-{200+len(CUSTOMERS):03d}'
 customer={'id':cid,'name':name,'visits':0,'last_days':0,'usual':[],'opted_in':body.opted_in,'avg_bill':0}
 CUSTOMERS.append(customer)
 DEMO_USERS[username]={'role':'customer','name':name,'customer_id':cid,'pin':body.pin,'opted_in':body.opted_in}
 DEMO.setdefault('consent',{})[cid]=body.opted_in
 DEMO.setdefault('notifications',{})[cid]=[]
 _demo_save(); _event('customer_registered',{'customer_id':cid,'customer':name})
 return {'ok':True,'username':username,'pin':body.pin,'customer_id':cid,'name':name,'role':'customer','opted_in':body.opted_in}
@app.post('/api/demo/merchant/create-pending-bill')
def create_pending_bill(body:PendingBillIn):
 if not body.items: raise HTTPException(400,'No bill items')
 if not body.customer_id: raise HTTPException(400,'Select the registered customer before generating a payment request. This links the bill to their dashboard and checks eligible cashback.')
 customer=next((c for c in CUSTOMERS if c['id']==body.customer_id),None)
 if not customer: raise HTTPException(404,'Customer not found')
 clean=[]; total=0
 for it in body.items:
  pid=str(it.get('id') or it.get('product_id') or '')
  prod=next((x for x in PRODUCTS if x['id']==pid),None)
  if not prod: raise HTTPException(400,'Unknown product')
  q=int(it.get('quantity',0))
  if q<1 or q>50: raise HTTPException(400,'Invalid quantity')
  if prod['stock']<q: raise HTTPException(400,f"Only {prod['stock']} {prod['unit']}(s) of {prod['name']} available")
  clean.append({'product_id':prod['id'],'name':prod['name'],'quantity':q,'unit':prod['unit'],'unit_price':prod['price'],'total':prod['price']*q})
  total+=prod['price']*q
 # Reserve one matching, unused customer cashback offer at bill creation so both sides see the same payable total.
 cashback=0; cashback_offer=None
 if customer and DEMO.get('consent',{}).get(customer['id'],customer.get('opted_in',False)):
  for offer in DEMO['offers']:
   if offer['customer_id']==customer['id'] and not offer.get('redeemed') and not offer.get('reserved_bill_id') and offer['product_id'] in [x['product_id'] for x in clean]:
    cashback=min(int(offer['cashback']),total)
    cashback_offer=offer
    break
 bid=f'SHOP-BILL-{DEMO["next_bill"]:05d}'; DEMO['next_bill']+=1
 pending={'bill_id':bid,'customer_id':customer['id'] if customer else None,'customer':customer['name'] if customer else 'Walk-in customer','items':clean,'subtotal':total,'amount':total,'cashback':cashback,'cashback_offer_id':cashback_offer['id'] if cashback_offer else None,'cashback_status':'Applied to this bill' if cashback else 'Not applicable','payable_amount':max(0,total-cashback),'status':'Waiting for customer payment','created_at':datetime.now().astimezone().isoformat(timespec='seconds')}
 if cashback_offer:
  cashback_offer['reserved_bill_id']=bid
  cashback_offer['status']='Reserved for bill '+bid
 DEMO.setdefault('pending_bills',[]).insert(0,pending)
 _event('bill_waiting',{'bill':pending})
 return {'ok':True,'bill':pending,'message':'Bill generated. Waiting for customer payment.'}
@app.get('/api/demo/customer/pending-bills')
def customer_pending_bills(request:Request):
 u=DEMO_USERS.get(request.state.session['username'])
 if not u or u['role']!='customer': raise HTTPException(403,'Customer login required')
 bills=[b for b in DEMO.get('pending_bills',[]) if b['status']=='Waiting for customer payment' and b.get('customer_id')==u['customer_id']]
 return {'bills':bills,'payments':[p for p in DEMO.get('payments',[]) if p.get('customer_id')==u['customer_id']],'offers':[o for o in DEMO['offers'] if o['customer_id']==u['customer_id']],'cashback_available':sum(int(o.get('cashback',0)) for o in DEMO['offers'] if o['customer_id']==u['customer_id'] and not o.get('redeemed') and not o.get('reserved_bill_id')),'cashback_used':sum(int(p.get('cashback',0)) for p in DEMO.get('payments',[]) if p.get('customer_id')==u['customer_id'])}
class CustomerPayIn(BaseModel):
 username:Optional[str]=None
 bill_id:str
 amount:float
@app.post('/api/demo/customer/pay')
async def customer_pay(body:CustomerPayIn, request:Request):
 u=DEMO_USERS.get(request.state.session['username'])
 if not u or u['role']!='customer': raise HTTPException(403,'Customer login required')
 bill=next((b for b in DEMO.get('pending_bills',[]) if b['bill_id']==body.bill_id),None)
 if not bill or bill['status']!='Waiting for customer payment': raise HTTPException(404,'Pending bill not found or already paid')
 if bill['customer_id'] and bill['customer_id']!=u['customer_id']: raise HTTPException(403,'This bill belongs to another customer')
 payable=float(bill.get('payable_amount',bill['amount']))
 if round(float(body.amount),2)!=round(payable,2): raise HTTPException(400,f"Amount must exactly match the payable total ₹{payable:.2f} after cashback")
 # Validate stock again before committing payment.
 for it in bill['items']:
  prod=next(x for x in PRODUCTS if x['id']==it['product_id'])
  if prod['stock']<it['quantity']: raise HTTPException(409,f"Insufficient stock for {prod['name']}")
 customer=next((c for c in CUSTOMERS if c['id']==u['customer_id']),None)
 cashback=int(bill.get('cashback',0)); redeemed=None
 offer_id=bill.get('cashback_offer_id')
 if cashback and offer_id:
  redeemed=next((o for o in DEMO['offers'] if o['id']==offer_id and o['customer_id']==u['customer_id'] and not o.get('redeemed')),None)
  if not redeemed: raise HTTPException(409,'The cashback offer is no longer available. Refresh the bill.')
  redeemed['redeemed']=True; redeemed['status']='Redeemed in '+bill['bill_id']; redeemed['redeemed_bill_id']=bill['bill_id']; redeemed['redeemed_payment_id']=f"SHOP-TX-{DEMO['next_payment']:05d}"; redeemed['reserved_bill_id']=None
  for notification in DEMO.get('notifications',{}).get(u['customer_id'],[]):
   if notification.get('id')==redeemed['id']:
    notification['redeemed']=True; notification['status']='Redeemed'; notification['redeemed_bill_id']=bill['bill_id']; notification['read']=True
 bill['cashback_status']='Used' if cashback else 'Not applicable'
 for it in bill['items']:
  prod=next(x for x in PRODUCTS if x['id']==it['product_id']); prod['stock']-=it['quantity']
 pid=f"SHOP-TX-{DEMO['next_payment']:05d}"; DEMO['next_payment']+=1
 paid=max(0,int(bill.get('payable_amount',bill['amount'])))
 payment={'payment_id':pid,'bill_id':bill['bill_id'],'customer':u['name'],'customer_id':u['customer_id'],'items':bill['items'],'subtotal':bill.get('subtotal',bill['amount']),'cashback':cashback,'cashback_status':'Used' if cashback else 'Not applicable','total_paid':paid,'payment_mode':'Customer UPI payment (demo)','status':'Paid (demo)','created_at':datetime.now().astimezone().isoformat(timespec='seconds')}
 DEMO['payments'].insert(0,payment); bill['status']='Paid'; bill['payment_id']=pid; bill['paid_by']=u['name']; bill['total_paid']=paid; bill['cashback_status']='Used' if cashback else 'Not applicable'; bill['cashback_used']=cashback
 STATE['sales_today']+=paid; STATE['transactions']+=1; STATE['cashback_spent']+=cashback
 STATE['recent'].insert(0,{'id':pid,'time':datetime.now().strftime('%H:%M'),'amount':paid,'items':', '.join(f"{x['quantity']} {x['name']}" for x in bill['items']),'status':'Paid (demo)'}); STATE['recent']=STATE['recent'][:8]
 announcement=f"Payment received. Rupees {paid}. Thank you {u['name']}."
 bill['status']='Paid'
 bill['paid_at']=datetime.now().astimezone().isoformat(timespec='seconds')
 ev=_event('payment_received',{'payment':payment,'bill':bill,'soundbox_text':announcement})
 if redeemed: _event('offer_redeemed',{'offer_id':redeemed['id'],'customer':u['name'],'cashback':cashback})
 _demo_save()
 # Push only after the paid state is durably saved, matching Munshi AI's WebSocket hub pattern.
 await soundbox_hub.broadcast({'type':'payment_received','payment':payment,'bill':bill,'soundbox_text':announcement,'event_id':ev['id']})
 return {'ok':True,'payment':payment,'bill':bill,'soundbox_text':announcement,'event_id':ev['id'],'message':'Payment successful. Merchant dashboard and Soundbox notified.'}

@app.post('/api/demo/merchant/reset-data')
def reset_demo_data(request:Request):
 if request.state.session.get('role')!='merchant': raise HTTPException(403,'Merchant login required')
 # Revoke every other session after reset; keep the initiating merchant signed in.
 current_username=request.state.session.get('username')
 for token, session in list(SESSIONS.items()):
  if session.get('username')!=current_username: SESSIONS.pop(token,None)
 # Keep the prototype's synthetic catalog, seed customers and demo credentials.
 PRODUCTS[:]=copy.deepcopy(PROTOTYPE_PRODUCTS)
 CUSTOMERS[:]=copy.deepcopy(PROTOTYPE_CUSTOMERS)
 DEMO_USERS.clear(); DEMO_USERS.update(copy.deepcopy(PROTOTYPE_USERS))
 STATE.clear(); STATE.update(copy.deepcopy(PROTOTYPE_STATE))
 SUPPLIER_ORDERS.clear(); save_supplier_orders()
 fresh=_demo_default(); DEMO.clear(); DEMO.update(fresh)
 # Remove all test transactions, offers, bills, notifications, activity and derived SQLite rows.
 with _db_conn() as conn:
  for table in ('entity_records','activity_log','offers','bills','payments','notifications'):
   conn.execute(f'DELETE FROM {table}')
 try: DEMO_FILE.unlink(missing_ok=True)
 except Exception: pass
 _demo_save()
 return {'ok':True,'message':'Prototype data restored. Test customers, offers, bills, payments and activity were cleared.','retained':{'products':len(PRODUCTS),'seed_customers':len(CUSTOMERS),'demo_accounts':len(DEMO_USERS)}}

@app.get('/api/demo/merchant/summary')
def demo_merchant_summary():
 _db_sync_all()
 sent,redeemed,rate=_offer_metrics()
 _demo_save()
 eligible=sum(1 for c in CUSTOMERS if DEMO.get('consent',{}).get(c['id'],c.get('opted_in',False)) and any(u.get('customer_id')==c['id'] for u in DEMO_USERS.values()))
 return {"offers_sent":sent,"offers_redeemed":redeemed,"redemption_rate":rate,"eligible_customers":eligible,"pending_bills":DEMO.get('pending_bills',[])[:100],"sales_today":STATE['sales_today'],"transactions":STATE['transactions'],"avg_bill":round(STATE['sales_today']/max(1,STATE['transactions'])),"payments":DEMO['payments'][:100],"offers":DEMO['offers'],"cashback_used_total":sum(int(p.get('cashback',0)) for p in DEMO['payments']),"products":PRODUCTS,"events":DEMO['events'][-30:]}
@app.get('/api/demo/events')
def demo_events(after:int=0): return {"events":[e for e in DEMO['events'] if e['id']>after],"latest_id":DEMO['next_event']-1}
