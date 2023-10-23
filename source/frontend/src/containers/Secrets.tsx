// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
    AppLayout,
    SpaceBetween,
    BreadcrumbGroup
} from '@awsui/components-react';

import ServiceNavigation from '../components/servicenavigation';
import CredentialManagerTable from '../components/CredentialManagerTable';
import { useCredentialManager } from '../actions/CredentialManagerHook';
import FlashMessage from '../components/FlashMessage';


const Breadcrumbs = () => (
  <BreadcrumbGroup
    items={[
      {
        text: 'Migration Management',
        href: '/admin/permissions'
      },
      {
        text: 'Secrets',
        href: '/secrets'
      }
    ]}
  />
);

const Secrets = (props) => {
    const [{ isLoading: secretDataIsLoading, data: secretData, error: secretDataErrorLoading }] = useCredentialManager();
    return (
        <>
            <AppLayout
                headerSelector="#header"
                navigation={<ServiceNavigation
                    userGroups={props.userGroups}
                />}
                notifications={<FlashMessage
                    notifications={props.notifications} />}
                breadcrumbs={<Breadcrumbs />}
                content={
                    <SpaceBetween direction="vertical" size="xs">
                        <CredentialManagerTable
                            items={secretData.secret}
                            isLoading={secretDataIsLoading}
                            errorLoading={secretDataErrorLoading}
                        />

                    </SpaceBetween>
                }
            />
        </>
    );
}

export default Secrets;
