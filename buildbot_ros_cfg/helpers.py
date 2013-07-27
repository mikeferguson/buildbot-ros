from buildbot.status import results

def success(result, s):
     return (result == results.SUCCESS)
