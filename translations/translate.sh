#!/bin/bash

if [[ "${0}" =~ "/" ]]; then
    cd `dirname "${0}"`
fi

for translation in *.{po,PO}; do
    if [ -e ${translation} ]; then
        lang=${translation%.po}
        lang=${lang%.PO}

        locale_dir=../sync/locale/"${lang}"/LC_MESSAGES

        if [ ! -d "${locale_dir}" ]; then
            mkdir -p "${locale_dir}"
        fi

        msgfmt -o "${locale_dir}"/localboxsync.mo "${translation}"
        rm -f "${lang}".mo

    fi
done
