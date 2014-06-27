## Using docker with buildbot-ros

Docker can help with simplifying the setup of buildbot-ros. An
example Dockerfile is provided to setup a buildbot-ros instance.

## Running the container

To build the container, you will want to create a folder with the
Dockerfile, and your key files (see below), in the command below,
the folder is assumed to be called 'buildbot-ros':

    docker build -t buildbot-ros-image buildbot-ros

After building the container, we need to specify a number of bindings
to make the buildbot work well:

    docker run -d -privileged=true -p 8010:8010 -p 127.0.0.1::22
               -v /etc/localtime:/etc/localtime:ro
               -v /var/www/building:/var/www/building:rw
               --name="buildbot-ros" buildbot-ros-image

We need to run the container privileged otherwise pbuilder/cowbuilder
will fail. This command binds port 8010 (which is the web interface for
buildbot), as well as making a local binding of ssh so that you can login
to update or debug the buildbot instance. We bind /var/www/building
so that the output from the buildbot is then stored on the local machine,
which can then be hosted. There might be better ways to do this, but
this is how I have done it thus far.

You might also need to add a "--dns x.y.z.w" if your DNS is not resolving
properly for any internal Debian repositories.

## Handling of keys

There are several keys that we need for a buildbot-ros instance. First,
you almost always need a private key for gpg signing of your debians.
This dockerfile will load secret.gpg and key.gpg to get the private and
public gpg key imported into the buildbot instance. If you are
using Github and private repositories or ssh access, you need an ssh
key that has already been added to Github. The id_rsa file should
be in the same 'buildbot-ros' folder with the Dockerfile, and the
example dockerfile expects it to be named 'buildbot_id_rsa'.

## Other issues

You will need to update reprepro-include.bash to use /root/buildbot-ros as the
BUILD_DIR

The aptrepo-create.bash should be modified to have:

    echo "SignWith: ABCD1234" >> distributions

Where the sign with comment is. Really, this script should be rewritten
in python so it can supports better args.
