require "ZomboidAura/Core"
require "ISUI/ISPanel"
require "ISUI/ISButton"
require "ISUI/ISComboBox"
local ZA = ZomboidAura
local Panel = ISPanel:derive("ZomboidAuraSettings")
local modeLabels = {"Aus", "Gesundheit", "Ausdauer", "Geraeuschrichtung", "Gesundheit + Geraeusch"}
local function choice(panel,x,y,width,options,selected)
    local combo = ISComboBox:new(x,y,width,26)
    combo:initialise()
    for _, label in ipairs(options) do combo:addOption(label) end
    combo.selected = selected or 1
    panel:addChild(combo)
    return combo
end
local function indexOf(list,value)
    for i,v in ipairs(list) do if v==value then return i end end
    return 1
end
function Panel:createChildren()
    ISPanel.createChildren(self)
    self.moveWithMouse = true
    self.backgroundColor = {r=0.08,g=0.08,b=0.1,a=0.98}
    self.rows = {}
    self.items = ZA.devices()
    self.page = 1
    self.capture = choice(self,16,78,380,{"Weltgeraeusche: aus (Adapter-API nutzen)","Weltgeraeusche: an (ungefaehre Ortung)"},ZA.captureWorld and 2 or 1)
    local refresh = ISButton:new(410,78,330,26,"Geraete neu laden",self,Panel.refresh)
    refresh:initialise(); self:addChild(refresh)
    self.prev = ISButton:new(16,480,90,28,"Zurueck",self,Panel.previous)
    self.prev:initialise(); self:addChild(self.prev)
    self.next = ISButton:new(116,480,90,28,"Weiter",self,Panel.following)
    self.next:initialise(); self:addChild(self.next)
    self.save = ISButton:new(440,480,140,28,"Speichern",self,Panel.apply)
    self.save:initialise(); self:addChild(self.save)
    self.close = ISButton:new(590,480,150,28,"Schliessen",self,Panel.hide)
    self.close:initialise(); self:addChild(self.close)
    self:buildPage()
end
function Panel:collect()
    for _, row in ipairs(self.rows) do
        local route = ZA.routes[row.item.id]
        route.mode=ZA.modes[row.mode.selected]
        route.player=row.player.selected-1
        route.brightness=({0.15,0.35,0.65,1})[row.brightness.selected]
        route.category=ZA.categories[row.category.selected]
    end
    ZA.captureWorld=self.capture.selected==2
end
function Panel:buildPage()
    for _,row in ipairs(self.rows) do
        self:removeChild(row.mode);self:removeChild(row.player)
        self:removeChild(row.brightness);self:removeChild(row.category)
    end
    self.rows={}
    for i=(self.page-1)*4+1, math.min(self.page*4,#self.items) do
        local item=self.items[i]
        local route=ZA.routes[item.id]
        local y=144+(i-(self.page-1)*4-1)*78
        local bright=1
        local minimum=2
        for j,v in ipairs({0.15,0.35,0.65,1}) do
            if math.abs(v-route.brightness)<minimum then bright=j;minimum=math.abs(v-route.brightness) end
        end
        self.rows[#self.rows+1]={item=item,y=y,
            mode=choice(self,16,y+24,248,modeLabels,indexOf(ZA.modes,route.mode)),
            player=choice(self,274,y+24,100,{"Spieler 1","Spieler 2","Spieler 3","Spieler 4"},route.player+1),
            brightness=choice(self,384,y+24,100,{"15 %","35 %","65 %","100 %"},bright),
            category=choice(self,494,y+24,246,ZA.categories,indexOf(ZA.categories,route.category))}
    end
end
function Panel:previous() self:collect();self.page=math.max(1,self.page-1);self:buildPage() end
function Panel:following() self:collect();self.page=math.min(math.max(1,math.ceil(#self.items/4)),self.page+1);self:buildPage() end
function Panel:refresh() self:collect();self.items=ZA.devices();self.page=1;self:buildPage() end
function Panel:apply() self:collect();self.message=ZA.saveConfig() and "Gespeichert." or "Speichern fehlgeschlagen. console.txt pruefen." end
function Panel:hide() self:setVisible(false);self:removeFromUIManager();ZA.panel=nil end
function Panel:prerender()
    ISPanel.prerender(self)
    self:drawText("Zomboid Aura | Alpha 0.1",16,12,1,1,1,1,UIFont.Medium)
    self:drawText("Pro Geraet oder kalibrierter LED-Zone eine Anzeige. Standard: aus.",16,42,0.8,0.8,0.8,1,UIFont.Small)
    self:drawText("Weltgeraeusche sind KI-Ereignisse, kein exakter Hoertest. Visual Sounds: noch kein Adapter.",16,112,1,0.75,0.35,1,UIFont.Small)
    for _,row in ipairs(self.rows) do self:drawText(row.item.name:sub(1,85),16,row.y,1,1,1,1,UIFont.Small) end
    if #self.items==0 then
        self:drawText("Keine Geraete. Windows-Bridge starten und 'Geraete neu laden' waehlen.",16,180,1,0.8,0.4,1,UIFont.Small)
    end
    self:drawText(self.message or "Touch/Maus bedienen. F10 oder Welt-Kontextmenue zum Oeffnen.",16,452,0.8,0.8,0.8,1,UIFont.Small)
end
function ZA.openSettings()
    if ZA.panel then ZA.panel:hide();return end
    local panel=Panel:new(math.max(0,(getCore():getScreenWidth()-760)/2),math.max(0,(getCore():getScreenHeight()-530)/2),760,530)
    panel:initialise();panel:addToUIManager();ZA.panel=panel
end
Events.OnKeyPressed.Add(function(key) if key==Keyboard.KEY_F10 then ZA.openSettings() end end)
Events.OnFillWorldObjectContextMenu.Add(function(player,context,objects,test)
    if not test then context:addOption("Aura Sync Einstellungen",nil,ZA.openSettings) end
end)
