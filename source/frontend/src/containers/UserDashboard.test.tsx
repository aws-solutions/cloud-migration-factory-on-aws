/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {render, screen, waitForElementToBeRemoved} from '@testing-library/react';
import React from "react";
import '@testing-library/jest-dom'
import UserDashboard from "./UserDashboard";
import {server} from "../setupTests";
import {rest} from "msw";
import {
  generateTestApps,
  generateTestDatabases,
  generateTestServers,
  generateTestWaves
} from "../__tests__/mocks/user_api";

const renderUserDashboardComponent = () => {
  return render(
    <div>
      <UserDashboard/>
      <div id='modal-root'/>
    </div>
  )
}

test('Dashboard loads and displays cards with no data', () => {

  // WHEN
  renderUserDashboardComponent();

  // THEN
  expect(screen.getByRole('heading', {name: 'Migration Factory overview'})).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Wave status'})).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Server migrations by month'})).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Operating systems'})).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Server Environments'})).toBeInTheDocument();
  expect(screen.getByRole('heading', {name: 'Server replication status'})).toBeInTheDocument();
});

test('Dashboard loads and displays cards with waves', async () => {
  // GIVEN
  const waves = generateTestWaves(5);
  const applications = generateTestApps(50);
  const servers = generateTestServers(20);
  const databases = generateTestDatabases(10);

  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.get('/user/server', (request, response, context) => {
      return response(
        context.status(200),
        context.json(servers)
      );
    }),
    rest.get('/user/app', (request, response, context) => {

      return response(
        context.status(200),
        context.json(applications)
      );
    }),
    rest.get('/user/database', (request, response, context) => {

      return response(
        context.status(200),
        context.json(databases)
      );
    }),
  );

  // WHEN
  renderUserDashboardComponent();
  await waitForElementToBeRemoved(() => screen.queryAllByText(/Loading/i));

  // THEN
  expect(screen.getByText('5')).toBeInTheDocument();
  expect(screen.getByText('50')).toBeInTheDocument();
  expect(screen.getByText('20')).toBeInTheDocument();
  expect(screen.getByText('10')).toBeInTheDocument();
});

test('Dashboard loads and displays cards with completed waves', async () => {
  // GIVEN
  const waves = generateTestWaves(2, {waveStatus: 'Completed'});
  const applications = generateTestApps(2, {waveId: waves[0].wave_id});
  const servers = generateTestServers(2, {appId: applications[0].app_id});
  const databases = generateTestDatabases(2, {appId: applications[0].app_id});

  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.get('/user/server', (request, response, context) => {
      return response(
        context.status(200),
        context.json(servers)
      );
    }),
    rest.get('/user/app', (request, response, context) => {

      return response(
        context.status(200),
        context.json(applications)
      );
    }),
    rest.get('/user/database', (request, response, context) => {

      return response(
        context.status(200),
        context.json(databases)
      );
    }),
  );

  // WHEN
  renderUserDashboardComponent();
  await waitForElementToBeRemoved(() => screen.queryAllByText(/Loading/i));

  // THEN
  // querying byTestId is the least preferred option, but this is a legacy component that I don't want to change
  // better would be e.g. to make 'completed waves' the label of the link and then query by label
  expect(screen.getByTestId('completed-waves').textContent).toEqual('2');
});
