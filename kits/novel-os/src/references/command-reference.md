# Novel-OS Command Reference

All commands run via: `python core/orchestrator.py <command> [args]`
Or the alias: `novel-os <command> [args]`

## init
Initialize a new project.

```
init --title TITLE --genre GENRE [--author AUTHOR]
```

## character
```
character add --name NAME --role {protagonist,antagonist,supporting}
character list
```

## plot
```
plot add --name NAME --description DESC
plot list
```

## plan
```
plan outline --chapters N --words N
plan chapter --number N [--pov CHARACTER]
```

## write
Draft a chapter via the Scribe agent.

```
write --chapter N [--draft-file PATH] [--dry-run]
```

## edit
Refine a chapter via the Editor agent.

```
edit --chapter N [--mode {line,developmental,pacing,dialogue,tension}] [--edited-file PATH] [--dry-run]
```

## validate
LLM Guardian continuity check.

```
validate --chapter N [--dry-run]
```

## approve
Gate — blocked if Guardian reported FAIL.

```
approve --chapter N
```

## check
Free deterministic continuity engine (no LLM). 9 checks: dormant threads, overdue threads, unresolved foreshadowing, absent characters, dead character reappearance, file consistency mismatches.

```
check [--chapter N]
```

## status
Show project state.

```
status
```

## export
```
export [--format {markdown,docx}]
```

## setup
Interactive provider configuration wizard.

```
setup
```

---

## Common flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--dry-run` | write, edit, validate | Save prompt to file; do not call LLM |
| `--help` | All | Show help |
