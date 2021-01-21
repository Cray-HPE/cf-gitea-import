
@Library('dst-shared@master') _

dockerBuildPipeline {
    repository = "cray"
    imagePrefix = ""
    app = "cf-gitea-import"
    name = "cf-gitea-import"
    description = "Base Image to facilitate importing product content into Gitea on Shasta systems."
    product = "csm"

    githubPushRepo = "Cray-HPE/cf-gitea-import"
    /*
        By default all branches are pushed to GitHub

        Optionally, to limit which branches are pushed, add a githubPushBranches regex variable
        Examples:
        githubPushBranches =  /master/ # Only push the master branch
        
        In this case, we push bugfix, feature, hot fix, master, and release branches
    */
    githubPushBranches =  /(bugfix\/.*|feature\/.*|hotfix\/.*|master|release\/.*)/ 
}
