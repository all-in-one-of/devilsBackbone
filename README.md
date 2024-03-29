# [https://github.com/all-in-one-of/devilsBackbone/blob/master/otls/sync.otl](https://github.com/all-in-one-of/devilsBackbone/blob/master/otls/sync.otl)

Please note that the whole project is under strong development and this is the first prototype
to proof the concept.

THIS IS ONLY FOR THE BRAVE!

Code documentation will follow when I actually have more efficient way to deal with Houdini's event mechanism.

More infos to follow soon.

========
Overview
========

The main goal of the project is to connect multiple instances of Houdini (and potentially more applications) over the network without forcing a network topology onto it, or being limited by the OS (cross OS connections are supported).
In other words a system which is able to run in the cloud but does not force this setup onto the user.

The basic concept is a message passing system which distributes changes over the network and stores them into other sessions. By that each user becomes a backup for each other user added to the fact, that they can work in real time on the same project.

This is a very early stage of the project and contributions are welcome. If you are interested in testing or contributing please contact me directly. In terms of documentation and roadmap more information will be release in the next few months.

As this is the first prototype there is not commitment to the API or the tools yet, because a lot of core architectural changes are planned to improve performance.

You can watch the tool in action. http://www.youtube.com/playlist?list=PLrPK6Xmq2-ts8mb6Se3UIN4OB_0gCmf-v

=====================
Concepts and Workflow
=====================

The main concept of the collaborative work sharing is the work of each user exists in a dedicated sandbox of each other user. So they can reference and access each others work.
Apart from the sandbox each context in Houdini is setup to fire events on user input, so the system can interpret and handle the data flow.

By default if a user wants to work on top of something which he does not own by creation, the user is supposed object merge it into his own workspace, prefixing the workspace of the user by
the dedicated variable for the user (meaning if the user is named adam the prefix is $ADAM). This workflow should be replaced by tooling and abstracted away from the user
because it is unnecessarily complicated and a source of errors.

Nodes that involve binary data (like the edit, sculpt or paint node) have to be committed into the system after the user is satisfied with the results. The tool shelf provides functionality for that.

By invoking the client each user connects to a message passing server, which is collecting and distributing all events triggered by Houdini.

Houdini events are handled in a one shot mechanism which means that as soon as the event gets fired a message will constructed and send off.
For high frequency event triggering this is posing an issue and will be addressed in the future.


=======
Install
=======

Just copy the folders desktop, toolbar, python2.7libs, otls to your Houdini settings folder or any folder inside of your HOUDINI_PATH.


List of features
----------------

    -> Soft real time collaboration
    -> Strict content management
    -> Light weight message passing
    -> No actual geometry content is transmitted by default
    -> User permission management
    -> Otl sharing without interrupting the workflow
    -> Automated backup mechanism for all participating users
    -> Default synchronisation for users joining late to the session
    -> Control sharing on per user per parameter basis with take based automated backups
    -> Node with binary state can be shared


List of limitations
-------------------

    -> No gallery entries can be used at the moment 
        (in theory they can, but they are slow and tend to choke the system)
    -> Message load can is high because of the way the Houdini event mechanism works
    -> Otls can't be shared on connecting late to a session, or on a recover connection
    -> Otl version can only be detected based on the not mandatory version string (work around
            would be fairly expensive at the moment)
    -> Some nodes trigger parm tuple changed events with a None entry for the parm, the only 
        work around for that is fairly expensive because the whole node must be initialized, which
        can choke performance on receiving machines completely
    -> Tools are missing completely to argument the workflow and to minimize potential user mistakes
    -> Nodes with binary states are not synced on connect or recover
    -> Expression tuples are not evaluated correctly, my be fixed by architecture change
    -> Problems if values are applies while the playback is used


=======
Roadmap
=======

The first thing that needs to be done is to stabilise the event loop handling. All events need to be processed in a deferred stable way so that Houdini more information about the actual state
of the nodes can be gathered. To work on top of each others work object merges and similar techniques should be used.

Improving of the connection process. On connection there needs to be enough information to know what otls are used and if all participants have the resources available.

Better solution for pressure handling (at the moment it applies data without being aware of user input which may produce hanging of Houdini).

Better support for all parameter types for control inversion.

Otls need to be checked more thorough for versioning and actual content (maybe even splitting with hotl?) to determine if all scenes are used in the same way.

Securing of otl sharing so the user can decide if the implementation of the shared data can be seen, modified, if parameter can be changed or if the otl is just a black box to be used.
A useful approach for that would be a facade node which is capable of decrypting time leased data handle passed the cook context on to a in memory decrypted node. That would provide protection
against opscript to see implementation and the data would exist only encrypted in memory. This can only be done successfully if the otl can request a secret from Houdini itself to prove it is running the 
correct context. A lot of thought has to go into this ...

==========================
High level system overview
==========================

The main focus inside of Houdini is inside of a subnet on obj level called bookkeeper. Every user is mirrored inside of the subnet. On connection all nodes but the bookkeeper are hooked up to specific event handling, that deals with capturing the user input. The nodes inside of the bookkeeper should not be touched or modified by the user under any circumstances. The only time events are hooked up into there is
if inversion of control is used.

The setup consists of five python files.

The server, which handles the distributing and filtering of messages.

The client, which sends and receives messages from the server.

The bookkeeper, which interprets the messages to Houdini commands and listens to the user triggered events from Houdini.

The dispatcher, which takes care of the low level sockets implementation for the server and the client.

The handleBinary file takes care of sending binary data like otls or the content of the paint node.
