# Twelve-Factor App Notes

This document is a compact study version of the Twelve-Factor App methodology.
It is used as the source document for the Lesson 10 RAG API homework.

## Codebase

A twelve-factor app is always tracked in a version control system.
There should be one codebase tracked in revision control and many deploys of that codebase.
Different deploys, such as staging and production, may run at the same time, but they come from the same codebase.

## Dependencies

A twelve-factor app explicitly declares and isolates dependencies.
It should not rely on implicit system packages already installed on the machine.
For Python services this usually means a requirements file, virtual environment, or container image.

## Config

Configuration should be stored in the environment.
Config includes database URLs, API keys, credentials, feature flags, and deploy-specific settings.
Secrets should not be committed into the codebase.

## Backing Services

Backing services are attached resources, such as databases, queues, caches, object storage, and external APIs.
The application should treat local and third-party services in the same way: as resources attached by configuration.

## Build, Release, Run

The delivery process should separate build, release, and run stages.
The build stage creates an executable bundle.
The release stage combines the build with configuration.
The run stage executes the application in the target environment.

## Processes

The application should run as one or more stateless processes.
State that must persist should be stored in backing services, not in local memory or local disk.

## Port Binding

A web application should export HTTP as a service by binding to a port.
It should not depend on a separate web server injected into the runtime environment.

## Concurrency

Applications should scale out by the process model.
Different types of work can be assigned to different process types, such as web workers, background workers, and scheduled jobs.

## Disposability

Processes should start quickly and shut down gracefully.
This makes deploys, scaling, and recovery faster and safer.

## Dev/Prod Parity

Development, staging, and production should be as similar as possible.
Large gaps between environments create bugs that only appear late in the delivery process.

## Logs

An application should treat logs as event streams.
It should write logs to stdout or stderr and let the execution environment collect, route, and store them.

## Admin Processes

One-off admin tasks should run in the same environment as the regular application.
Examples include database migrations, reindexing jobs, and maintenance scripts.

