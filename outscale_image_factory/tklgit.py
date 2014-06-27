#!/usr/bin/env python3
"""
Generate a list of Turnkey Linux repositories.

Dependencies:
 http://jacquev6.github.io/PyGithub/v1/
"""
import sys
import json
import github


def parse_entry(json_input_record):
    '''
    Take a record from the json input file and return a list of
    repositories.

    The record from the json input file is the tuple:
    (github_account, repo_map)

    Repo_map is a dict of repositories and branches to use. If it is
    empty all repositories on the github account are used.

    The output is a list of triplets:
    [(appliance_name, repository_url, branch), ...].
    '''
    account, repo_map = json_input_record
    gh = github.Github()
    user = gh.get_user(account)
    repo_list = []
    for repo in user.get_repos():
        repo_branch = 'master'
        if repo_map:
            repo_branch = repo_map.get(repo.name)
            if repo_branch is None:
                continue
        repo_list.append((repo.name, repo.url, repo_branch))
    return repo_list


def main():
    """
    Main function.
    """
    if not sys.argv[1:]:
        sys.stderr.write('Usage: {} tklgit_input.json\n'.format(sys.argv[0]))
        sys.exit(1)
    sys.stderr.write('Parsing input file\n')
    if sys.argv[1] == '-':
        json_input = json.load(sys.stdin)
    else:
        with open(sys.argv[1]) as input_file:
            json_input = json.load(input_file)
    output = []
    for record in json_input:
        output.extend(parse_entry(record))
    sys.stderr.write('Dumping {} repositories to stdout\n'.format(len(output)))
    json.dump(output, sys.stdout, sort_keys=True, indent=4, separators=(',', ': '))


if __name__ == '__main__':
    main()
