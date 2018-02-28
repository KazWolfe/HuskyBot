import discord

def memberHasRole(member, role_id):
    for r in member.roles:
        if r.id == role_id:
            return True
            
    return False
