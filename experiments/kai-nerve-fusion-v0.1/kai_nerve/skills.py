from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class Skill:
    name:str; mode:str; preconditions:tuple[str,...]; abort_if:tuple[str,...]
    success:tuple[str,...]; max_duration_s:float; cooldown_s:float; notes:str

SKILLS={
"scan_safe":Skill("scan_safe","read_only",
 ("source health known","observation provenance retained"),("source process failed",),
 ("fresh snapshot recorded","hazards classified or explicitly unknown"),2.0,0.0,
 "No known threat detected never means safe."),
"flee_creeper":Skill("flee_creeper","physical",
 ("armed lease valid","single control owner","gameplay context","fresh non-replay observation",
 "creeper vector known","movement calibration verified","terrain escape corridor verified"),
 ("observation stale/unknown","HUD exits","cliff/lava corridor unknown","control ownership lost",
 "player death","stream session changes"),
 ("creeper distance increasing","outside critical radius","player remains on traversable terrain"),
 1.5,2.5,"Escape before combat; dry-run before physical actuation."),
"escape_unknown":Skill("escape_unknown","physical",
 ("armed lease valid","single control owner","fresh damage/event evidence",
 "source vector or safe retreat vector known","terrain escape corridor verified"),
 ("source/vector unknown and no safe retreat","stale/replay observation","control ownership lost","HUD exits"),
 ("damage stops","distance from source increases or shelter reached"),1.2,2.0,
 "Unknown is dangerous but does not authorize blind movement."),
"recover_stream":Skill("recover_stream","system",
 ("stream health degraded","no physical action in progress"),("world-changing command required",),
 ("capture sequence advances","frame age below budget","session change recorded"),12.0,5.0,
 "Recover by layers; never restart multiple bridges blindly.")
}
def skill_list():return [asdict(SKILLS[k]) for k in sorted(SKILLS)]
