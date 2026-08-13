"""Client du canal de commande DCS (hook dcs_claude_control.lua).

Envoie du Lua exécuté dans la mission via UDP loopback : affichage écran,
spawn (avion/sol/navire) avec positionnement + accrochage terrain, ordres de tir.
"""
import socket

import cities
import prefabs

# Préambule Lua partagé : trouve le joueur, résout un POINT DE RÉFÉRENCE
# (player/mark/bullseye/airbase/coords), applique le décalage cap+distance, puis
# ACCROCHE au terrain adéquat (terre pour sol, eau pour navires ; rien pour l'air).
# Définit : x, z, hdg, pc, side, country, gname. Tokens remplis côté Python.
_PRELUDE = r'''
local ok, err = pcall(function()
  local function claude_player()
    for _,co in pairs({0,1,2}) do
      for _,g in pairs(coalition.getGroups(co)) do
        for _,unit in pairs(g:getUnits()) do
          if unit:getPlayerName() then return unit end
        end
      end
    end
  end
  local function surf_ok(px, pz, wantLand)
    local s = land.getSurfaceType({x=px, y=pz})
    if wantLand then return s==1 or s==4 or s==5 else return s==2 or s==3 end
  end
  local function claude_snap(px, pz, cat)
    if cat == "air" then return px, pz end
    local wantLand = (cat ~= "ship")
    if surf_ok(px, pz, wantLand) then return px, pz end
    for r=250,25000,250 do
      for a=0,350,20 do
        local qx = px + r*math.cos(math.rad(a))
        local qz = pz + r*math.sin(math.rad(a))
        if surf_ok(qx, qz, wantLand) then return qx, qz end
      end
    end
    return px, pz
  end
  local u = claude_player()
  if not u then env.info("CLAUDE_SPAWN ERR no player") return end
  local pp = u:getPoint()
  local pc = u:getCoalition()
  local side = "__SIDE__"
  local country
  if side == "friendly" then country = u:getCountry()
  else country = (pc == 2) and 0 or 2 end
  local hdg = 0
  do local pos = u:getPosition() hdg = math.atan2(pos.x.z, pos.x.x) end
  local ref = "__REF__"
  local rx, rz
  if ref == "coords" then
    local v = coord.LLtoLO(__LAT__, __LON__, 0) rx, rz = v.x, v.z
  elseif ref == "bullseye" then
    local b = coalition.getMainRefPoint(pc) rx, rz = b.x, b.z
  elseif ref == "airbase" then
    local best
    for _,ab in pairs(world.getAirbases()) do
      local nm = ab:getName() or ""
      if string.find(string.lower(nm), string.lower("__PLACE__"), 1, true) then best = ab break end
    end
    if not best then env.info("CLAUDE_SPAWN ERR airbase introuvable: __PLACE__") return end
    local ap = best:getPoint() rx, rz = ap.x, ap.z
  elseif ref == "mark" then
    local best, bd
    for _,m in pairs(world.getMarkPanels() or {}) do
      if m.pos then local dx=m.pos.x-pp.x local dz=m.pos.z-pp.z local d=dx*dx+dz*dz
        if not bd or d<bd then bd=d best=m end end
    end
    if not best then env.info("CLAUDE_SPAWN ERR aucun repere F10") return end
    rx, rz = best.pos.x, best.pos.z
  else
    rx, rz = pp.x, pp.z
  end
  local baseb = 0
  if ref == "player" and __RELATIVE__ then baseb = hdg end
  local brg = baseb + math.rad(__BEARING__)
  local dist = __DIST__
  local x = rx + dist*math.cos(brg)
  local z = rz + dist*math.sin(brg)
  x, z = claude_snap(x, z, "__CATEGORY__")
  _G.__claude_n = (_G.__claude_n or 0) + 1
  local gname = "__GPREFIX__"..math.floor(timer.getTime())..".".._G.__claude_n
'''

_TAIL = r'''
end)
if not ok then env.info("CLAUDE_SPAWN ERR "..tostring(err)) end
'''

_AIR_BODY = r'''
  local alt, speed = __ALT__, __SPEED__
  local units = {}
  for i=1,__COUNT__ do
    units[i] = {
      ["type"]="__TYPE__", ["name"]=gname.."-"..i,
      ["x"]=x + (i-1)*60, ["y"]=z, ["alt"]=alt, ["alt_type"]="BARO",
      ["speed"]=speed, ["heading"]=0, ["skill"]="High",
      ["payload"]={["pylons"]={},["fuel"]=5000,["flare"]=60,["chaff"]=60,["gun"]=100},
      ["callsign"]={1,1,i}, __UNITEXTRA__
    }
  end
  local group = {
    ["name"]=gname, ["task"]="__GROUPTASK__", ["units"]=units,
    ["route"]={["points"]={[1]={["x"]=x,["y"]=z,["alt"]=alt,["alt_type"]="BARO",
      ["type"]="Turning Point",["action"]="Turning Point",["speed"]=speed,["speed_locked"]=true,
      ["task"]=__ROUTETASK__}}},
  }
  coalition.addGroup(country, Group.Category.AIRPLANE, group)
  _G.__claude_groups = _G.__claude_groups or {}
  table.insert(_G.__claude_groups, {name=gname, ally=(side=="friendly")})
  env.info("CLAUDE_SPAWN OK "..gname.." "..side.." __TYPE__ country="..country)
'''

_GROUND_BODY = r'''
  local units = {}
  for i=1,__COUNT__ do
    units[i] = { ["type"]="__TYPE__", ["name"]=gname.."-"..i,
      ["x"]=x+(i-1)*25, ["y"]=z+(i-1)*25, ["heading"]=0, ["skill"]="High" }
  end
  local group = { ["name"]=gname, ["task"]="Ground Nothing", ["units"]=units,
    ["route"]={["points"]={[1]={["x"]=x,["y"]=z,["type"]="Turning Point",
      ["action"]="Off Road",["speed"]=0}}} }
  coalition.addGroup(country, Group.Category.GROUND, group)
  _G.__claude_groups = _G.__claude_groups or {}
  table.insert(_G.__claude_groups, {name=gname, ally=(side=="friendly")})
  env.info("CLAUDE_SPAWN OK "..gname.." "..side.." __TYPE__ country="..country)
'''

_SHIP_BODY = r'''
  local units = {}
  for i=1,__COUNT__ do
    units[i] = { ["type"]="__TYPE__", ["name"]=gname.."-"..i,
      ["x"]=x+(i-1)*120, ["y"]=z+(i-1)*120, ["heading"]=0, ["skill"]="High" }
  end
  local group = { ["name"]=gname, ["task"]="", ["units"]=units,
    ["route"]={["points"]={[1]={["x"]=x,["y"]=z,["type"]="Turning Point",
      ["action"]="Turning Point",["speed"]=0}}} }
  coalition.addGroup(country, Group.Category.SHIP, group)
  _G.__claude_groups = _G.__claude_groups or {}
  table.insert(_G.__claude_groups, {name=gname, ally=(side=="friendly")})
  env.info("CLAUDE_SPAWN OK "..gname.." "..side.." __TYPE__ country="..country)
'''

_SPAWN_LUA = _PRELUDE + _AIR_BODY + _TAIL
_SPAWN_GROUND_LUA = _PRELUDE + _GROUND_BODY + _TAIL
_SPAWN_SHIP_LUA = _PRELUDE + _SHIP_BODY + _TAIL


# Ordonne aux groupes ALLIÉS spawnés par Claude d'engager l'ennemi.
_ENGAGE_LUA = r'''
local n = 0
for _,e in ipairs(_G.__claude_groups or {}) do
  if e.ally then
    local g = Group.getByName(e.name)
    if g and g:isExist() then
      local con = g:getController()
      pcall(function() con:setOption(0, 2) end)   -- ROE = weapon free
      pcall(function() con:setOnOff(true) end)
      pcall(function() con:setTask({id="EngageTargets",
        params={targetTypes={"Air","Ground Units","Ships"}}}) end)
      n = n + 1
    end
  end
end
env.info("CLAUDE_ENGAGE "..n)
return tostring(n)
'''


# Corps : groupe (sol/mer) construit depuis une composition d'unités (__UNITSPEC__).
_GROUP_SPEC_BODY = r'''
  local spec = { __UNITSPEC__ }
  local units = {}
  for i,s in ipairs(spec) do
    units[i] = { ["type"]=s.t, ["name"]=gname.."-"..i,
      ["x"]=x+s.dx, ["y"]=z+s.dz, ["heading"]=0, ["skill"]="High" }
  end
  local group = { ["name"]=gname, ["task"]="__GROUPTASK2__", ["units"]=units,
    ["route"]={["points"]={[1]={["x"]=x,["y"]=z,["type"]="Turning Point",
      ["action"]="__ROUTEACTION__",["speed"]=0}}} }
  coalition.addGroup(country, __CATENUM__, group)
  _G.__claude_groups = _G.__claude_groups or {}
  table.insert(_G.__claude_groups, {name=gname, ally=(side=="friendly")})
  env.info("CLAUDE_SPAWN OK "..gname.." "..side.." prefab "..#units.." unites country="..country)
'''

# Corps : marquage/effet sur la position résolue (fumigène / fusée / cercle F10).
_MARK_BODY = r'''
  local y = land.getHeight({x=x, y=z})
  local kind = "__KIND__"
  if kind == "smoke" then
    trigger.action.smoke({x=x,y=y,z=z}, __COLOR__)
  elseif kind == "flare" then
    trigger.action.signalFlare({x=x,y=y,z=z}, __COLOR__, 0)
  elseif kind == "circle" then
    trigger.action.circleToAll(-1, (math.floor(timer.getTime()*10) % 100000),
      {x=x,y=y,z=z}, __RADIUS__, {1,0,0,1}, {1,0,0,0.12}, 1, false)
  end
  env.info("CLAUDE_MARK OK "..kind)
'''

# Corps : objet statique (bâtiment, dépôt, FARP...).
_STATIC_BODY = r'''
  local st = { ["type"]="__TYPE__", ["name"]=gname, ["x"]=x, ["y"]=z,
    ["heading"]=0, ["category"]="__SCAT__", ["dead"]=false }
  coalition.addStaticObject(country, st)
  env.info("CLAUDE_SPAWN OK static "..gname.." __TYPE__ country="..country)
'''

_PREFAB_LUA = _PRELUDE + _GROUP_SPEC_BODY + _TAIL
_MARK_LUA = _PRELUDE + _MARK_BODY + _TAIL
_STATIC_LUA = _PRELUDE + _STATIC_BODY + _TAIL


def _lua_str(s):
    """Encode une chaîne Python en littéral Lua entre guillemets, échappé."""
    s = (s or "").replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\r", "").replace("\n", "\\n")
    return '"' + s + '"'


class DcsControl:
    def __init__(self, host="127.0.0.1", port=5011, timeout=2.0):
        self._addr = (host, int(port))
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(timeout)

    def send_lua(self, lua, wait_reply=True):
        """Envoie du Lua à exécuter dans la mission ; renvoie la réponse (str) ou None."""
        self._sock.sendto(lua.encode("utf-8"), self._addr)
        if not wait_reply:
            return None
        try:
            data, _ = self._sock.recvfrom(8192)
            return data.decode("utf-8", "ignore")
        except socket.timeout:
            return None

    def ping(self, timeout=2.0):
        """True si le hook répond (toute réponse = canal vivant)."""
        return self.send_lua('return "pong"') is not None

    def mission(self, code, wait_reply=True):
        """Exécute du code dans le BAC À SABLE de scripting de mission.

        L'environnement 'mission' de net.dostring_in n'expose pas trigger/coalition
        directement, mais fournit a_do_script(...) qui exécute dans le vrai sandbox.
        On enveloppe donc le code dans a_do_script([==[ ... ]==])."""
        safe = code.replace("]==]", "]=]")   # ne casse pas le long-bracket
        return self.send_lua("a_do_script([==[%s]==])" % safe, wait_reply)

    def out_text(self, text, seconds=15):
        """Affiche un message à l'écran dans DCS (bandeau)."""
        return self.mission("trigger.action.outText(%s, %d, false)"
                            % (_lua_str(text), int(seconds)))

    # Tâches par type de mission (route point task + tâche de groupe + extra unité).
    _MISSIONS = {
        "cap": {"grouptask": "CAP",
                "route": '{["id"]="ComboTask",["params"]={["tasks"]={[1]={["id"]="EngageTargets",["params"]={["targetTypes"]={[1]="Air"}}}}}}',
                "extra": ""},
        "cas": {"grouptask": "CAS",
                "route": '{["id"]="ComboTask",["params"]={["tasks"]={}}}',
                "extra": ""},
        "tanker": {"grouptask": "Refueling",
                   "route": '{["id"]="ComboTask",["params"]={["tasks"]={[1]={["id"]="Tanker",["params"]={}},[2]={["id"]="Orbit",["params"]={["pattern"]="Race-Track"}}}}}',
                   "extra": '["frequency"]=251000000,'},
        "awacs": {"grouptask": "AWACS",
                  "route": '{["id"]="ComboTask",["params"]={["tasks"]={[1]={["id"]="AWACS",["params"]={}},[2]={["id"]="Orbit",["params"]={["pattern"]="Race-Track"}}}}}',
                  "extra": '["frequency"]=251000000,'},
    }

    @staticmethod
    def _loc_repl(side, count, unit_type, category, gprefix,
                  reference, place, lat, lon, bearing_deg, distance_nm, relative):
        """Construit les tokens communs (position + terrain). Résout ville->coords."""
        ref = reference or "player"
        if ref == "city":
            ll = cities.resolve(place)
            if not ll:
                raise ValueError(f"ville inconnue : {place}")
            lat, lon = ll
            ref = "coords"
        return {
            "__REF__": ref,
            "__LAT__": str(float(lat) if lat is not None else 0.0),
            "__LON__": str(float(lon) if lon is not None else 0.0),
            "__PLACE__": str(place or "").replace('"', "").replace("]", "").replace("[", ""),
            "__BEARING__": str(float(bearing_deg)),
            "__DIST__": str(float(distance_nm) * 1852.0),
            "__RELATIVE__": "true" if relative else "false",
            "__COUNT__": str(int(max(1, count))),
            "__TYPE__": str(unit_type).replace('"', ""),
            "__SIDE__": "friendly" if side == "friendly" else "enemy",
            "__CATEGORY__": category,
            "__GPREFIX__": gprefix,
        }

    def spawn_aircraft(self, aircraft, side="enemy", count=1,
                       bearing_deg=90, distance_nm=15, altitude_ft=15000,
                       speed_ms=250, relative=False, mission="cap",
                       reference="player", place=None, lat=None, lon=None):
        """Groupe d'avions (air-start). Position via `reference` (player/mark/bullseye/
        airbase/city/coords) + décalage cap/distance. relative n'agit que pour player."""
        repl = self._loc_repl(side, count, aircraft, "air", "Claude-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        repl["__ALT__"] = str(float(altitude_ft) * 0.3048)
        repl["__SPEED__"] = str(float(speed_ms))
        m = self._MISSIONS.get(mission, self._MISSIONS["cap"])
        repl["__GROUPTASK__"] = m["grouptask"]
        repl["__ROUTETASK__"] = m["route"]
        repl["__UNITEXTRA__"] = m["extra"]
        lua = _SPAWN_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    def spawn_ground(self, unit_type, side="enemy", count=1,
                     bearing_deg=90, distance_nm=2, relative=False,
                     reference="player", place=None, lat=None, lon=None):
        """Groupe AU SOL (accroché à la terre la plus proche)."""
        repl = self._loc_repl(side, count, unit_type, "ground", "ClaudeG-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        lua = _SPAWN_GROUND_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    def spawn_ship(self, unit_type, side="enemy", count=1,
                   bearing_deg=90, distance_nm=10, relative=False,
                   reference="player", place=None, lat=None, lon=None):
        """Groupe de NAVIRES (accroché à l'eau la plus proche)."""
        repl = self._loc_repl(side, count, unit_type, "ship", "ClaudeS-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        lua = _SPAWN_SHIP_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    def order_engage(self):
        """Ordonne à tous les groupes ALLIÉS spawnés par Claude d'engager l'ennemi.
        S'exécute dans le bac à sable mission (Group/Controller/env)."""
        return self.mission(_ENGAGE_LUA)

    def spawn_prefab(self, name, side="enemy", bearing_deg=90, distance_nm=5,
                     relative=False, reference="player", place=None, lat=None, lon=None):
        """Fait apparaître un PREFAB (paquet tactique) : site SAM, colonne blindée,
        CAP, groupe naval... Variante rouge/bleu selon `side`."""
        pf = prefabs.get(name)
        if not pf:
            raise ValueError(f"prefab inconnu : {name}")
        cat = pf["cat"]
        if cat == "air":
            a = prefabs.air_for(pf, side)
            return self.spawn_aircraft(
                a["aircraft"], side=side, count=a.get("count", 2),
                mission=a.get("mission", "cap"), bearing_deg=bearing_deg,
                distance_nm=distance_nm, relative=relative, reference=reference,
                place=place, lat=lat, lon=lon)
        # sol ou navire : composition d'unités
        spacing = 120 if cat == "ship" else 40
        spec = prefabs.grid_spec(prefabs.units_for(pf, side), spacing)
        spec_lua = ",".join('{t="%s",dx=%d,dz=%d}'
                            % (s["t"].replace('"', ""), s["dx"], s["dz"]) for s in spec)
        catmap = {"ground": ("Group.Category.GROUND", "Ground Nothing", "Off Road"),
                  "ship": ("Group.Category.SHIP", "", "Turning Point")}
        catenum, gtask, action = catmap.get(cat, catmap["ground"])
        repl = self._loc_repl(side, 1, "prefab", cat, "ClaudeP-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        repl["__UNITSPEC__"] = spec_lua
        repl["__CATENUM__"] = catenum
        repl["__GROUPTASK2__"] = gtask
        repl["__ROUTEACTION__"] = action
        lua = _PREFAB_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    _COLORS = {"green": 0, "vert": 0, "red": 1, "rouge": 1, "white": 2, "blanc": 2,
               "orange": 3, "blue": 4, "bleu": 4}

    def battlefield_mark(self, kind="smoke", color="red", radius_nm=5,
                         reference="player", place=None, lat=None, lon=None,
                         bearing_deg=0, distance_nm=0, relative=False):
        """Marque une position : 'smoke' (fumigène), 'flare' (fusée), 'circle' (cercle F10)."""
        repl = self._loc_repl("friendly", 1, "mark", "air", "Mark-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        repl["__KIND__"] = kind if kind in ("smoke", "flare", "circle") else "smoke"
        repl["__COLOR__"] = str(self._COLORS.get(str(color).lower(), 1))
        repl["__RADIUS__"] = str(float(radius_nm) * 1852.0)
        lua = _MARK_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    # Objets statiques : nom convivial -> (type DCS, catégorie statique).
    _STATICS = {
        "fuel": ("Fuel tank", "Fortifications"),
        "warehouse": ("Warehouse", "Warehouses"),
        "hangar": ("Hangar A", "Warehouses"),
        "comms": ("Comms tower M", "Fortifications"),
        "bunker": ("Bunker", "Fortifications"),
        "farp": ("FARP", "Heliports"),
        "container": ("Container red 1", "Cargos"),
        "tent": ("CV_59_Tent1", "Fortifications"),
    }

    def spawn_static(self, kind, side="enemy", bearing_deg=90, distance_nm=1,
                     relative=False, reference="player", place=None, lat=None, lon=None):
        """Fait apparaître un objet STATIQUE (dépôt, entrepôt, FARP, tour...)."""
        st = self._STATICS.get(str(kind).lower())
        if not st:
            raise ValueError(f"statique inconnu : {kind}")
        stype, scat = st
        repl = self._loc_repl(side, 1, "static", "ground", "ClaudeSt-",
                              reference, place, lat, lon, bearing_deg, distance_nm, relative)
        repl["__TYPE__"] = stype
        repl["__SCAT__"] = scat
        lua = _STATIC_LUA
        for k, v in repl.items():
            lua = lua.replace(k, v)
        return self.mission(lua)

    def highlight_control(self, query, hid=77):
        """Encadre la commande du cockpit dont le libellé (hint) correspond le
        mieux à `query`. Fonctionne dans l'env loader (GetClickableElements +
        a_cockpit_highlight). Renvoie le libellé encadré, ou None si rien trouvé."""
        q = (query or "").lower().replace('"', "").replace("\\", "")
        lua = (
            'local q=%s '
            'local words={} for w in q:gmatch("%%a+") do words[#words+1]=w end '
            'local els=GetClickableElements() '
            'local bk,bh,bs=nil,nil,0 '
            'for k,v in pairs(els) do local h=tostring(v.hint or ""):lower() local s=0 '
            'for _,w in ipairs(words) do if #w>=3 and h:find(w,1,true) then s=s+1 end end '
            'if s>bs then bs=s bk=k bh=v.hint end end '
            'if bk and bs>0 then a_cockpit_remove_highlight(%d) a_cockpit_highlight(%d,bk) return bh end '
            'return "NOMATCH"'
        ) % (_lua_str(q), hid, hid)
        r = self.send_lua(lua)
        return None if (r is None or r == "NOMATCH") else r

    def get_frequency(self, device=38):
        """Fréquence radio en MHz du device (F/A-18C : 38=COMM1, 39=COMM2).
        Lue dans l'env loader via GetDevice(id):get_frequency(). None si indispo."""
        r = self.send_lua(
            "local ok,f=pcall(function() return GetDevice(%d):get_frequency() end) "
            "if ok and type(f)=='number' then return tostring(f) else return '' end"
            % int(device))
        try:
            return round(float(r) / 1e6, 3) if r else None
        except Exception:
            return None

    def remove_highlight(self, hid=77):
        """Retire l'encadrement de commande."""
        return self.send_lua("a_cockpit_remove_highlight(%d) return \"OK\"" % hid)

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass
